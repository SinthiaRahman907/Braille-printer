import RPi.GPIO as GPIO
import time
import math

# ── GPIO pin map (BCM) ─────────────────────────────────────────────────────────
X_STEP_PIN       = 21   # X-axis STEP
X_DIR_PIN        = 20   # X-axis DIR
Y_STEP_PIN       = 12   # Y-axis STEP
Y_DIR_PIN        = 16   # Y-axis DIR
PAPER_SENSOR_PIN = 17   # IR paper sensor: LOW when paper present
SOLENOID_PIN     = 13   # MOSFET gate for punch solenoid

# ── Motion constants ───────────────────────────────────────────────────────────
X_STEPS_PER_MM   = 80     # with 1/16 microstep
Y_STEPS_PER_MM   = 46
DEFAULT_FEEDRATE = 1000.0 # mm/min

# ── GPIO setup ────────────────────────────────────────────────────────────────
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
# Outputs
GPIO.setup(X_STEP_PIN,   GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(X_DIR_PIN,    GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(Y_STEP_PIN,   GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(Y_DIR_PIN,    GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(SOLENOID_PIN, GPIO.OUT, initial=GPIO.LOW)
# Input with pull-up
GPIO.setup(PAPER_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

class StepperMotor:
    """DIR/STEP control for one axis."""
    def __init__(self, step_pin, dir_pin, steps_per_mm):
        self.step_pin     = step_pin
        self.dir_pin      = dir_pin
        self.steps_per_mm = steps_per_mm
        self.current_dir  = None

    def step(self, forward: bool):
        """One microstep; forward=True => positive direction."""
        if forward != self.current_dir:
            GPIO.output(self.dir_pin, GPIO.HIGH if forward else GPIO.LOW)
            self.current_dir = forward
        GPIO.output(self.step_pin, GPIO.HIGH)
        time.sleep(0.00005)
        GPIO.output(self.step_pin, GPIO.LOW)
        time.sleep(0.00005)

class BraillePrinter:
    """Controls X/Y steppers, punch solenoid, and paper sensor."""
    def __init__(self):
        self.x             = StepperMotor(X_STEP_PIN, X_DIR_PIN, X_STEPS_PER_MM)
        self.y             = StepperMotor(Y_STEP_PIN, Y_DIR_PIN, Y_STEPS_PER_MM)
        self.feedrate      = DEFAULT_FEEDRATE
        self.absolute_mode = True
        self.x_pos = 0.0
        self.y_pos = 0.0
        self.solenoid_on = False

    def wait_for_paper(self):
        """Block until PAPER_SENSOR_PIN reads LOW (paper present)."""
        print("[printer] Waiting for paper…")
        while GPIO.input(PAPER_SENSOR_PIN) == GPIO.HIGH:
            time.sleep(0.01)
        print("[printer] Paper detected.")

    def solenoid(self, state: bool | None):
        """Turn punch solenoid ON/OFF (None = no change)."""
        if state is None:
            return
        GPIO.output(SOLENOID_PIN, GPIO.HIGH if state else GPIO.LOW)
        self.solenoid_on = bool(state)

    def punch_dot(self, duration: float = 0.1):
        """Energize solenoid for `duration` seconds."""
        GPIO.output(SOLENOID_PIN, GPIO.HIGH)
        self.solenoid_on = True
        time.sleep(duration)
        GPIO.output(SOLENOID_PIN, GPIO.LOW)
        self.solenoid_on = False

    def set_feedrate(self, f: float):
        if f and f > 0:
            self.feedrate = f

    def move(self, x_target=None, y_target=None, feed=None):
        """Linear move to (x_target, y_target) in mm."""
        if feed:
            self.set_feedrate(feed)

        # compute deltas
        if self.absolute_mode:
            dx_mm = (x_target - self.x_pos) if x_target is not None else 0.0
            dy_mm = (y_target - self.y_pos) if y_target is not None else 0.0
            final_x = self.x_pos + dx_mm
            final_y = self.y_pos + dy_mm
        else:
            dx_mm = x_target or 0.0
            dy_mm = y_target or 0.0
            final_x = self.x_pos + dx_mm
            final_y = self.y_pos + dy_mm

        dx_steps = int(round(dx_mm * X_STEPS_PER_MM))
        dy_steps = int(round(dy_mm * Y_STEPS_PER_MM))
        x_dir    = dx_steps >= 0
        y_dir    = dy_steps >= 0
        dx_steps = abs(dx_steps)
        dy_steps = abs(dy_steps)

        if dx_steps == 0 and dy_steps == 0:
            return

        # timing
        distance = math.hypot(dx_mm, dy_mm)
        secs     = distance / (self.feedrate / 60.0)
        total    = max(dx_steps, dy_steps)
        delay    = secs / total if total else 0

        # Bresenham‐style coordinated stepping
        x_err = y_err = 0
        x_cnt = y_cnt = 0
        for _ in range(total):
            if x_cnt < dx_steps:
                x_err += dx_steps
                if x_err >= total:
                    self.x.step(x_dir)
                    x_err -= total
                    x_cnt += 1
            if y_cnt < dy_steps:
                y_err += dy_steps
                if y_err >= total:
                    self.y.step(y_dir)
                    y_err -= total
                    y_cnt += 1
            if delay > 0:
                time.sleep(max(0, delay - 0.0001))

        self.x_pos, self.y_pos = final_x, final_y

    # ── Minimal G-code support ──────────────────────────────────────────────────
    def execute_gcode_line(self, line: str):
        l = line.strip()
        if not l or l[0] in (';', '('):
            return
        parts = l.split()
        cmd   = parts[0].upper()
        args  = {}
        for p in parts[1:]:
            if len(p) > 1:
                args[p[0].upper()] = float(p[1:])
        if cmd in ('G0', 'G1'):
            self.move(args.get('X'), args.get('Y'), args.get('F'))
        elif cmd == 'G90':
            self.absolute_mode = True
        elif cmd == 'G91':
            self.absolute_mode = False
        elif cmd == 'G4':
            wait = args.get('S', 0.0)
            if 'P' in args:
                p = args['P']
                wait = (p / 1000.0) if p > 10 else p
            if wait > 0:
                time.sleep(wait)
        elif cmd in ('M3', 'M4'):
            self.solenoid(True)
        elif cmd == 'M5':
            self.solenoid(False)

    def execute_gcode(self, lines: list[str]):
        for ln in lines:
            try:
                self.execute_gcode_line(ln)
            except Exception as e:
                print("[G-code error]", e)
