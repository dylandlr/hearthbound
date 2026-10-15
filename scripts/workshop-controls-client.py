"""Real native screen and block-picking interaction via xdotool, never a UI mock."""
import re
import subprocess
import time
import threading


def run_setup(api):
    def lines():
        return (api['OUT'] / 'client.log').read_text().splitlines()

    def click(x, y):
        subprocess.run(['xdotool', 'mousemove', '--sync', str(round(x)), str(round(y)), 'click', '1'], check=True)
        time.sleep(.25)

    def screen():
        rows = [line for line in lines() if 'HB_WORKSHOP_SCREEN x=' in line]
        assert rows, 'No actual workshop screen initialized'
        return {key: int(re.search(key + r'=(\d+)', rows[-1])[1]) for key in ['x', 'y', 'width', 'height']}

    def button(kind):
        g = screen(); x, y, width, height = [g[k] for k in ['x', 'y', 'width', 'height']]
        if isinstance(kind, int): click(2 * (x + 64), 2 * (y + 50 + kind * 22))
        elif kind == 'target': click(2 * (x + 134), 2 * (y + 142))
        elif kind == 'save': click(2 * (x + 12 + (width - 100) / 4), 2 * (y + height - 20))
        elif kind == 'stop': click(2 * (x + 18 + 3 * (width - 100) / 4), 2 * (y + height - 20))
        elif kind == 'resume': click(2 * (x + width - 62), 2 * (y + 163))
        elif kind == 'close': click(2 * (x + width - 44), 2 * (y + height - 20))

    def open_screen():
        before = len([line for line in lines() if 'HB_WORKSHOP_SCREEN x=' in line])
        follow = threading.Event()
        def track():
            while not follow.wait(.1):
                try: api['aim']()
                except OSError: pass
        camera = threading.Thread(target=track, daemon=True)
        camera.start()
        try:
            api['aim'](); time.sleep(.5)
            deadline = time.monotonic() + 12
            attempts = 0
            while len([line for line in lines() if 'HB_WORKSHOP_SCREEN x=' in line]) <= before:
                if time.monotonic() >= deadline:
                    raise AssertionError('Real right-click did not open worker screen after '
                                         + str(attempts) + ' attempts; recent controls: '
                                         + str([line for line in lines() if 'HB_WORKSHOP_' in line][-12:]))
                subprocess.run(['xdotool', 'click', '3'], check=True)
                attempts += 1
                time.sleep(.4)
            print('HB_WORKSHOP_OPEN_UI_PASS real_right_click attempts=' + str(attempts), flush=True)
            time.sleep(.3)
        finally:
            follow.set(); camera.join(timeout=2)
        return screen()

    def save_order():
        before = len([line for line in lines() if 'HB_WORKSHOP_SCREEN x=' in line])
        button('save')
        api['wait_for'](lambda: len([line for line in lines() if 'HB_WORKSHOP_SCREEN x=' in line]) > before, 10, 'server acknowledges UI save')

    def choose(slot, x, y, z):
        button(slot)
        time.sleep(.2)
        # Observer feet remain on the same floor; only the camera/player moves.
        if slot == 3:
            api['command'](f'tp {api["PLAYER"]} {x + .5} {y + 1} {z + 2.8} 180 35.16')
        else:
            api['command'](f'tp {api["PLAYER"]} {x + .5} {y} {z + 3} 180 24.13')
        time.sleep(.45)
        before = len([line for line in lines() if 'HB_WORKSHOP_PICK kind=' in line])
        subprocess.run(['xdotool', 'click', '3'], check=True)
        api['wait_for'](lambda: len([line for line in lines() if 'HB_WORKSHOP_PICK kind=' in line]) > before, 10, 'world block selection ' + str(slot))
        time.sleep(.3)

    api['command']('deop ' + api['PLAYER'])
    open_screen()
    api['screenshot']('controls-empty.png')
    choose(0, 42, -60, 0)
    choose(1, 49, -60, 0)
    choose(2, 55, -60, 0)
    # Escape returns from selection without losing the other chosen stations.
    button(3); time.sleep(.2)
    subprocess.run(['xdotool', 'key', 'Escape'], check=True)
    time.sleep(.5)
    choose(3, 46, -61, 3)
    button('target')
    subprocess.run(['xdotool', 'key', 'ctrl+a', 'type', '--delay', '40', '2'], check=True)
    time.sleep(.3)
    api['screenshot']('controls-configured.png')
    save_order()
    api['wait_for'](lambda: 'HearthboundMillOrder:' in api['rcon'].execute(f'data get entity {api["WORKER"]} ForgeData'), 10, 'UI starts persisted work order')
    for amount in (3, 2):
        button('target')
        subprocess.run(['xdotool', 'key', 'ctrl+a', 'type', '--delay', '40', str(amount)], check=True)
        save_order()
        api['wait_for'](lambda: re.search(r':\s*' + str(amount) + r'\s*$', api['rcon'].execute(f'data get entity {api["WORKER"]} ForgeData.HearthboundMillOrder.TargetFlour')), 10, 'UI saves active flour target')
    print('HB_WORKSHOP_EDIT_UI_PASS active_target_3_then_2', flush=True)
    assert 'HB_WORKSHOP_CONTROLS_AUTH_PASS' in api['command']('execute positioned 48 -60 0 run hearthbound ci_workshop_controls')
    button('close')
    print('HB_WORKSHOP_SETUP_UI_PASS mouse_open four_world_picks escape_cancel numeric_target non_operator_start', flush=True)
    return {'open': open_screen, 'button': button, 'screen': screen, 'save': save_order}
