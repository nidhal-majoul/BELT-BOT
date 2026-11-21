import queue
import threading
import customtkinter as ctk   # pip install customtkinter
from PIL import Image          # pip install pillow
from virtual_arm import VirtualArm, ArmView
from position_manager import PositionManager

# settings
REAL_PORT = "COM4"           # port of the real myCobot
VIEW_W, VIEW_H = 640, 480    # size of the 3D view
# limits of each joint in degrees (from the official model)
LIMITS = [(-168, 168), (-140, 140), (-150, 150), (-150, 150), (-155, 160), (-180, 180)]


# all the robot actions happen in this thread, one after another,
# so the window never freezes while the robot is moving
class RobotWorker(threading.Thread):

    def __init__(self, ui_queue):
        super().__init__(daemon=True)
        self._jobs = queue.Queue()
        self._ui = ui_queue           # to send things to the window
        self.stop_event = threading.Event()
        self.twin = None              # the virtual myCobot (it's always the 3D view)
        self.real = None              # the real myCobot, only in REAL mode
        self.slider_angles = None     # last angles asked by the sliders

    def submit(self, job):
        self._jobs.put(job)

    def active(self):
        # the robot that receives the orders: real if connected, if not the virtual one
        return self.real if self.real is not None else self.twin

    def _send_angles(self):
        angles = self.active().read_angles()
        if self.real is not None:
            self.twin.show_angles(angles)   # the twin copies the real robot
        self._ui.put(("angles", angles))

    def run(self):
        # the virtual arm sends its joints to the window, and the window draws them
        self.twin = VirtualArm(on_state=lambda qpos: self._ui.put(("state", qpos)))
        self.twin.show_angles([0] * 6)
        while True:
            try:
                job = self._jobs.get(timeout=0.3)
            except queue.Empty:
                # nothing to do: in REAL mode we keep copying the real robot to the twin
                # (so if you move it by hand, you see it move on the screen)
                if self.real is not None:
                    try:
                        self._send_angles()
                    except Exception:
                        pass
                continue
            if job is None:   # None = close the program
                break
            if getattr(job, "quiet", False):
                # small jobs (the sliders): no "busy", so the window doesn't block
                try:
                    job(self)
                except Exception as error:
                    self._ui.put(("error", f"{type(error).__name__}: {error}"))
                continue
            self._ui.put(("busy", True))
            try:
                job(self)
                self._send_angles()
            except Exception as error:
                self._ui.put(("error", f"{type(error).__name__}: {error}"))
            finally:
                self._ui.put(("busy", False))
        if self.real is not None:
            self.real.close()
        self.twin.close()


class TwinApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")
        self.title("myCobot 280 - Digital Twin")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.positions = PositionManager().load()
        self._ui = queue.Queue()
        self.worker = RobotWorker(self._ui)
        self._busy = False
        self._view_image = None

        self._build()
        self._refresh_positions()
        self.arm_view = ArmView(VIEW_W, VIEW_H)   # draws the 3D view (in this thread)
        self.worker.start()
        self.after(33, self._read_queue)

    # ---------------- window ----------------
    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        left = ctk.CTkFrame(self)
        left.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")
        right = ctk.CTkFrame(self)
        right.grid(row=0, column=1, padx=(0, 12), pady=12, sticky="ns")

        # left: 3D view + log
        self.view = ctk.CTkLabel(left, text="Loading 3D model...", width=VIEW_W, height=VIEW_H)
        self.view.pack(padx=10, pady=10)
        self.lbl_angles = ctk.CTkLabel(left, text="Angles: -", font=("Consolas", 14))
        self.lbl_angles.pack()
        self.log = ctk.CTkTextbox(left, height=110)
        self.log.pack(fill="x", padx=10, pady=10)

        # right: controls
        ctk.CTkLabel(right, text="myCobot Digital Twin", font=("Arial", 20, "bold")).pack(pady=(12, 4))
        self.lbl_status = ctk.CTkLabel(right, text="VIRTUAL mode", text_color="#1dcd9f")
        self.lbl_status.pack()

        self.mode = ctk.CTkSegmentedButton(right, values=["VIRTUAL", "REAL"], command=self._change_mode)
        self.mode.set("VIRTUAL")
        self.mode.pack(pady=8, padx=12, fill="x")
        self.port = ctk.CTkEntry(right, placeholder_text="Port of the real robot")
        self.port.insert(0, REAL_PORT)
        self.port.pack(padx=12, fill="x")

        # one slider per joint (they move the virtual robot)
        self.sliders = []
        box = ctk.CTkFrame(right)
        box.pack(pady=10, padx=12, fill="x")
        for i, (low, high) in enumerate(LIMITS):
            ctk.CTkLabel(box, text=f"J{i + 1}", width=28).grid(row=i, column=0, padx=4)
            s = ctk.CTkSlider(box, from_=low, to=high, command=self._slider_moved)
            s.set(0)
            s.grid(row=i, column=1, padx=4, pady=3, sticky="ew")
            self.sliders.append(s)

        row = ctk.CTkFrame(right, fg_color="transparent")
        row.pack(padx=12, fill="x")
        self.btn_home = ctk.CTkButton(row, text="Home", width=80, command=lambda: self._run(lambda w: w.active().go_home()))
        self.btn_open = ctk.CTkButton(row, text="Open", width=80, command=lambda: self._run(lambda w: w.active().open_gripper()))
        self.btn_close = ctk.CTkButton(row, text="Close", width=80, command=lambda: self._run(lambda w: w.active().close_gripper()))
        for b in (self.btn_home, self.btn_open, self.btn_close):
            b.pack(side="left", padx=2, expand=True)

        row2 = ctk.CTkFrame(right, fg_color="transparent")
        row2.pack(padx=12, pady=6, fill="x")
        self.btn_release = ctk.CTkButton(row2, text="Release motors", command=self._release)
        self.btn_lock = ctk.CTkButton(row2, text="Lock motors", command=self._lock)
        self.btn_release.pack(side="left", padx=2, expand=True)
        self.btn_lock.pack(side="left", padx=2, expand=True)

        # save positions
        ctk.CTkLabel(right, text="Positions", font=("Arial", 15, "bold")).pack(pady=(10, 2))
        self.name = ctk.CTkEntry(right, placeholder_text="Name (e.g. pick)")
        self.name.pack(padx=12, fill="x")
        self.btn_save = ctk.CTkButton(right, text="Save current position", command=self._save)
        self.btn_save.pack(padx=12, pady=6, fill="x")

        self.combo = ctk.CTkComboBox(right, values=[""], state="readonly")
        self.combo.pack(padx=12, fill="x")
        row3 = ctk.CTkFrame(right, fg_color="transparent")
        row3.pack(padx=12, pady=6, fill="x")
        self.btn_go = ctk.CTkButton(row3, text="Go to", width=110, command=self._go_to)
        self.btn_delete = ctk.CTkButton(row3, text="Delete", width=110, fg_color="#a33", hover_color="#822", command=self._delete)
        self.btn_go.pack(side="left", padx=2, expand=True)
        self.btn_delete.pack(side="left", padx=2, expand=True)

        self.btn_play = ctk.CTkButton(right, text="▶  Play all positions", command=self._play_all)
        self.btn_play.pack(padx=12, pady=(10, 4), fill="x")
        self.btn_cycle = ctk.CTkButton(right, text="⟳  Pick and place cycle", command=self._pick_and_place)
        self.btn_cycle.pack(padx=12, pady=(0, 4), fill="x")
        self.btn_stop = ctk.CTkButton(right, text="■  Stop", fg_color="#a33", hover_color="#822", command=self._stop)
        self.btn_stop.pack(padx=12, pady=(0, 12), fill="x")

        self._update_buttons()

    # ---------------- helpers ----------------
    def _write(self, text):
        self.log.insert("end", text + "\n")
        self.log.see("end")

    def _run(self, job, text=None):
        # sends an action to the robot thread (only one at a time)
        if self._busy:
            self._write("The robot is busy, wait a moment")
            return
        if text:
            self._write(text)
        self._busy = True
        self._update_buttons()
        self.worker.submit(job)

    def _is_real(self):
        return self.mode.get() == "REAL"

    def _update_buttons(self):
        idle = "normal" if not self._busy else "disabled"
        for b in (self.btn_home, self.btn_open, self.btn_close, self.btn_save, self.btn_go,
                  self.btn_delete, self.btn_play, self.btn_cycle):
            b.configure(state=idle)
        real_state = idle if self._is_real() else "disabled"
        self.btn_release.configure(state=real_state)
        self.btn_lock.configure(state=real_state)
        # the sliders only move the virtual robot
        slider_state = "normal" if (not self._is_real() and not self._busy) else "disabled"
        for s in self.sliders:
            s.configure(state=slider_state)
        # you can't change the mode while the robot is moving (no real + virtual at the same time)
        self.mode.configure(state="normal" if not self._busy else "disabled")
        self.btn_stop.configure(state="normal" if self._busy else "disabled")

    def _refresh_positions(self):
        names = self.positions.names()
        self.combo.configure(values=names if names else [""])
        self.combo.set(names[-1] if names else "")

    # ---------------- actions ----------------
    def _change_mode(self, value):
        if value == "REAL":
            port = self.port.get().strip()

            def connect(w):
                from arm import Arm   # only imported when we really need the real robot
                w.real = Arm(port)
            self._run(connect, f"Connecting to the real robot in {port}...")
        else:
            def disconnect(w):
                if w.real is not None:
                    w.real.close()
                    w.real = None
            self._run(disconnect, "Back to VIRTUAL mode")
        self.lbl_status.configure(text=f"{value} mode", text_color="#e0a030" if value == "REAL" else "#1dcd9f")
        self._update_buttons()

    def _slider_moved(self, _value):
        # we don't send every tiny movement as a job: we keep only the last angles
        angles = [round(s.get(), 1) for s in self.sliders]
        first = self.worker.slider_angles is None
        self.worker.slider_angles = angles
        if first:
            def move(w):
                target, w.slider_angles = w.slider_angles, None
                w.twin.show_angles(target)
                self._ui.put(("angles", target))
            move.quiet = True
            self.worker.submit(move)

    def _release(self):
        self._run(lambda w: w.real.release_motors(), "Motors released: move the robot by hand")

    def _lock(self):
        self._run(lambda w: w.real.lock_motors(), "Motors locked")

    def _save(self):
        name = self.name.get().strip()
        if not name:
            self._write("Write a name for the position first")
            return

        def save(w):
            angles = w.active().read_angles()
            self.positions.add(name, angles)
            self._ui.put(("saved", (name, angles)))
        self._run(save)

    def _go_to(self):
        name = self.combo.get()
        if not name:
            return
        angles = self.positions.get(name)
        self._run(lambda w: w.active().move_angles(angles), f"Going to '{name}'")

    def _delete(self):
        name = self.combo.get()
        if name:
            self.positions.delete(name)
            self._refresh_positions()
            self._write(f"Deleted '{name}'")

    def _play_all(self):
        names = self.positions.names()
        if not names:
            self._write("There are no saved positions")
            return

        def play(w):
            w.stop_event.clear()
            for name in names:
                if w.stop_event.is_set():
                    self._ui.put(("log", "Stopped"))
                    break
                self._ui.put(("log", f"→ {name}"))
                w.active().move_angles(self.positions.get(name))
        self._run(play, f"Playing {len(names)} positions")

    def _pick_and_place(self):
        # the same movement as pick_and_place.py, using the recorded positions
        needed = ["above_pick", "pick", "above_box", "box"]
        missing = [n for n in needed if n not in self.positions.names()]
        if missing:
            self._write(f"Missing positions: {missing}")
            return
        p = {n: self.positions.get(n) for n in self.positions.names()}
        real = self._is_real()

        def cycle(w):
            arm = w.active()
            if not real:
                # in the simulation the belt brings a piece to the pick point
                stop_x = w.twin.tcp_for(p["pick"])[0]
                self._ui.put(("log", "Belt: a new piece is coming"))
                w.twin.new_piece(stop_x)
            steps = [("open", None), ("move", "above_pick"), ("move", "pick"), ("close", None),
                     ("move", "above_pick"), ("move", "above_box"), ("move", "box"), ("open", None),
                     ("move", "above_box"), ("move", "home" if "home" in p else None)]
            for action, name in steps:
                if w.stop_event.is_set():
                    self._ui.put(("log", "Stopped"))
                    return
                if action == "open":
                    arm.open_gripper()
                elif action == "close":
                    arm.close_gripper()
                elif name is None:
                    arm.go_home()
                else:
                    self._ui.put(("log", f"→ {name}"))
                    arm.move_angles(p[name])
            self._ui.put(("log", "Piece in the box ✓"))
        self.worker.stop_event.clear()
        self._run(cycle, "Pick and place cycle")

    def _stop(self):
        # the robot finishes the movement it's doing and then stops
        self.worker.stop_event.set()

    # ---------------- messages from the robot thread ----------------
    def _read_queue(self):
        frame = None
        try:
            while True:
                kind, value = self._ui.get_nowait()
                if kind == "state":
                    frame = value                 # we only draw the newest state
                elif kind == "angles":
                    self.lbl_angles.configure(text="Angles: " + "  ".join(f"{a:7.1f}" for a in value))
                    if self._is_real() or self._busy:
                        for s, a in zip(self.sliders, value):
                            s.set(a)
                elif kind == "busy":
                    self._busy = value
                    self._update_buttons()
                elif kind == "saved":
                    name, angles = value
                    self._refresh_positions()
                    self._write(f"Saved '{name}': {angles}")
                elif kind == "log":
                    self._write(value)
                elif kind == "error":
                    self._write("ERROR " + value)
                    if self._is_real() and self.worker.real is None:
                        # we couldn't connect to the real robot -> back to virtual
                        self.mode.set("VIRTUAL")
                        self.lbl_status.configure(text="VIRTUAL mode", text_color="#1dcd9f")
                        self._update_buttons()
        except queue.Empty:
            pass
        if frame is not None:
            image = self.arm_view.draw(frame)
            self._view_image = ctk.CTkImage(Image.fromarray(image), size=(VIEW_W, VIEW_H))
            self.view.configure(image=self._view_image, text="")
        self.after(33, self._read_queue)

    def on_close(self):
        self.worker.stop_event.set()
        self.worker.submit(None)
        self.worker.join(timeout=10)
        self.arm_view.close()
        self.destroy()


if __name__ == "__main__":
    TwinApp().mainloop()
