# Pathfinder reaction test - MicroPython
#
# Button order on the PCB:
#   0 = top-left     = D3 = GPIO29
#   1 = top-right    = D0 = GPIO26
#   2 = bottom-left  = D2 = GPIO28
#   3 = bottom-right = D1 = GPIO27
#
# XIAO RP2040 onboard RGB LED (active-low):
#   red = GPIO17, green = GPIO16, blue = GPIO25

from machine import Pin
import time
import urandom


# ---------- Hardware and game settings ----------

BUTTON_GPIOS = (29, 26, 28, 27)

XIAO_LED_R_GPIO = 17
XIAO_LED_G_GPIO = 16
XIAO_LED_B_GPIO = 25

DEBOUNCE_MS = 25
MIN_WAIT_MS = 1500
MAX_WAIT_MS = 10000
REACTION_TIMEOUT_MS = 2000
MAX_SCORES = 10


# ---------- Hardware initialisation ----------

# A pressed switch connects its GPIO to GND.
buttons = [Pin(gpio, Pin.IN, Pin.PULL_UP) for gpio in BUTTON_GPIOS]

# The onboard RGB LED is active-low: value 0 turns a colour on.
led_r = Pin(XIAO_LED_R_GPIO, Pin.OUT, value=1)
led_g = Pin(XIAO_LED_G_GPIO, Pin.OUT, value=1)
led_b = Pin(XIAO_LED_B_GPIO, Pin.OUT, value=1)

# Stores the latest valid reaction times in milliseconds.
scores = []


# ---------- LED helpers ----------

def set_xiao_rgb(red=False, green=False, blue=False):
    """Set the XIAO onboard RGB status LED."""
    led_r.value(0 if red else 1)
    led_g.value(0 if green else 1)
    led_b.value(0 if blue else 1)


def show_average(average_ms):
    """Show the rolling average: green <=250 ms, yellow <=400 ms, red otherwise."""
    if average_ms <= 250:
        set_xiao_rgb(False, True, False)
    elif average_ms <= 400:
        set_xiao_rgb(True, True, False)
    else:
        set_xiao_rgb(True, False, False)


# ---------- Button helpers ----------

def pressed_button():
    """Return the pressed button index (0..3), or -1 when no button is pressed."""
    for index, button in enumerate(buttons):
        if button.value() == 0:
            return index
    return -1


def wait_all_released():
    """Wait until all buttons have stayed released for DEBOUNCE_MS."""
    released_since = time.ticks_ms()

    while True:
        if pressed_button() == -1:
            if time.ticks_diff(time.ticks_ms(), released_since) >= DEBOUNCE_MS:
                return
        else:
            released_since = time.ticks_ms()

        time.sleep_ms(2)


def wait_for_press(timeout_ms):
    """Return (button_index, press_time_ms), or (-1, None) after timeout_ms."""
    start = time.ticks_ms()
    candidate = -1
    candidate_since = start

    while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
        current = pressed_button()
        now = time.ticks_ms()

        if current != candidate:
            candidate = current
            candidate_since = now

        if candidate != -1 and time.ticks_diff(now, candidate_since) >= DEBOUNCE_MS:
            # candidate_since is the first sampled instant of the press, so it
            # does not include the time the player keeps the key held down.
            return candidate, candidate_since

        time.sleep_ms(2)

    return -1, None


# ---------- Reaction game ----------

def random_wait_ms():
    """Generate a random delay from MIN_WAIT_MS to MAX_WAIT_MS."""
    span = MAX_WAIT_MS - MIN_WAIT_MS + 1
    return MIN_WAIT_MS + (urandom.getrandbits(16) % span)


def add_score(reaction_ms):
    """Store a valid reaction time and retain only the most recent MAX_SCORES."""
    scores.append(reaction_ms)
    if len(scores) > MAX_SCORES:
        scores.pop(0)


def average_score():
    """Return the average valid reaction time in milliseconds."""
    return sum(scores) // len(scores)


def play_round():
    """
    Orange: wait without pressing.
    White: GO, press any of the four buttons as quickly as possible.
    Red: pressed too early.
    Blue: timed out.
    Green/yellow/red after a valid press: rolling-average category.
    """
    wait_all_released()

    # Orange means that the random waiting phase has started.
    set_xiao_rgb(True, True, False)
    early_button, _ = wait_for_press(random_wait_ms())

    if early_button != -1:
        set_xiao_rgb(True, False, False)
        print("Too early - round cancelled")
        time.sleep_ms(1000)
        return

    # White is the GO signal. Any button is valid in this reaction test.
    set_xiao_rgb(True, True, True)
    start = time.ticks_ms()
    button, press_time = wait_for_press(REACTION_TIMEOUT_MS)

    if button == -1:
        set_xiao_rgb(False, False, True)
        print("Timed out")
        time.sleep_ms(1000)
        return

    reaction_ms = time.ticks_diff(press_time, start)
    add_score(reaction_ms)
    average_ms = average_score()

    print("Button %d | %d ms | average of %d: %d ms" % (
        button + 1, reaction_ms, len(scores), average_ms
    ))

    show_average(average_ms)
    time.sleep_ms(1500)


def boot_animation():
    """Check red, green and blue channels when the board starts."""
    for colour in ((True, False, False), (False, True, False), (False, False, True)):
        set_xiao_rgb(*colour)
        time.sleep_ms(180)
    set_xiao_rgb(False, False, True)


def main():
    boot_animation()
    wait_all_released()
    print("Reaction test ready: orange = wait, white = press any button")

    while True:
        play_round()
        time.sleep_ms(300)


main()
