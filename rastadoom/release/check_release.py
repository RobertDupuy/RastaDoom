#!/usr/bin/env python3
"""Run the release CAR on native AltirraSDL and feed actual ARM-rendered frames.

The adapter substitutes the Pico's memory/GPIO protocol. This is a functional
test, not a simultaneous dual-core timing test or a hardware FPS measurement.
"""
from pathlib import Path
import argparse, base64, hashlib, json, shutil, subprocess, sys, time, zlib

p = argparse.ArgumentParser()
for name in ('sdk', 'os', 'car', 'engine', 'wad', 'out'):
    p.add_argument(name, type=Path)
p.add_argument('--tv', choices=('ntsc', 'pal'), default='ntsc')
args = p.parse_args()
here = Path(__file__).resolve().parent
sdk, rom, car, out = (getattr(args, k).resolve() for k in ('sdk', 'os', 'car', 'out'))
out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(sdk / 'sdk/python'))
from altirra_bridge import AltirraBridge

assert zlib.crc32(rom.read_bytes()) == 0x29f133f7
assert b'STEP ' not in car.read_bytes()
(out / 'pico-windows.bin').write_bytes(car.read_bytes()[16:] + bytes(16384))
shutil.copy(here.parent / 'checkpoints/pico-model.atdevice', out / 'pico-model.atdevice')
log = open(out / 'server-private.log', 'w')
server = subprocess.Popen([str(sdk / 'AltirraBridgeServer'), '--bridge=tcp:127.0.0.1:0',
                           '--machine=800XL', '--memory=64K', '--no-basic'], stdout=log, stderr=log)
worker = None
engine_log = open(out / 'engine.jsonl', 'w')
trace, events, published, stages = [], [], {}, {}
model = None
last_consumed, last_service, live_start = 0, -100, None
joy_state = console_state = None
plan = [
    ('title', 2, 'centre', False),
    ('open_menu_hold', 6, 'centre', True),
    ('release_menu', 2, 'centre', False),
    ('new_game_hold', 6, 'centre', True),
    ('release_new', 2, 'centre', False),
    ('episode_hold', 6, 'centre', True),
    ('release_episode', 2, 'centre', False),
    ('difficulty_hold', 8, 'centre', True),
    ('release_start', 2, 'centre', False),
    ('move', 8, 'up', False),
    ('turn', 6, 'right', False),
    ('shoot_move', 12, 'up', True),
    ('release_play', 4, 'centre', False),
]
total = sum(n for _, n, _, _ in plan)

def action(k):
    if k < 0:
        return ('startup', 'centre', False)
    for name, n, direction, fire in plan:
        if k < n:
            return name, direction, fire
        k -= n
    return ('done', 'centre', False)

try:
    token = Path(f'/tmp/altirra-bridge-{server.pid}.token')
    for _ in range(100):
        if token.exists() and 'token-file:' in (out / 'server-private.log').read_text():
            break
        if server.poll() is not None:
            raise RuntimeError('Native Altirra server exited')
        time.sleep(.05)
    worker = subprocess.Popen(['node', str(here / 'engine_worker.mjs'),
                               str(args.engine.resolve()), str(args.wad.resolve())],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)

    def arm(command, phase):
        worker.stdin.write(json.dumps(command) + '\n')
        worker.stdin.flush()
        line = worker.stdout.readline()
        if not line:
            raise RuntimeError('ARM worker exited')
        reply = json.loads(line)
        if 'error' in reply:
            raise RuntimeError(reply['error'])
        record = {k: v for k, v in reply.items() if k not in ('frame', 'mailbox')}
        record.update(command=command, phase=phase)
        engine_log.write(json.dumps(record) + '\n')
        engine_log.flush()
        if 'frame' in reply:
            trace.append(record)
            events.extend(reply['events'])
        print('ARM', reply['produced'], phase, 'STATE', reply['state'],
              'MENU', reply['menu'], reply['menuName'], 'AMMO', reply['bullets'], flush=True)
        return reply

    with AltirraBridge.from_token_file(str(token)) as a:
        a.pause()
        for k, v in [('kernel', str(rom)), ('video', args.tv), ('fastboot', 'off'),
                     ('siopatch', 'off'), ('fppatch', 'off')]:
            a.config(k, v)
        cfg = a.config()
        a.device_set('custom', True, path=str(out / 'pico-model.atdevice'), allowunsafe=True)
        a.cold_reset()
        a.pause()

        def controls(direction='centre', fire=False, start=False, select=False, option=False):
            global joy_state, console_state
            j, c = (direction, fire), (start, select, option)
            if j != joy_state:
                a.joy(0, direction, fire)
                joy_state = j
            if c != console_state:
                a.consol(start=start, select=select, option=option)
                console_state = c

        def publish(reply):
            mb = base64.b64decode(reply['mailbox'])
            for off, n in [(0xf0, 4), (0xf5, 2), (0xa0, 40)]:
                a.memload(0x108000 + off, mb[off:off + n])
            if 'frame' in reply:
                raw, bank = base64.b64decode(reply['frame']), reply['pending']
                assert len(raw) == 16384 and raw[0x3fe0:0x3fe4] == b'RD5F'
                a.memload(0x100000 + bank * 16384, raw)
                published[bank] = raw
                a.memload(0x1080fc, bytes([bank, 1]))

        for f in range(1, 2501):
            k = model['produced'] - live_start if model and live_start is not None else -1
            phase, direction, fire = action(k)
            controls(direction, fire)
            a.frame(1)
            a.regs()
            cur, mb = a.peek(0x80, 1)[0], a.peek(0xd500, 256)
            screen = a.peek(0x2900, 120)
            assert not screen.startswith(b'STEP '), (f, screen)
            assert b'STOPPED' not in screen, (f, screen)
            if cur == 9 and model and model['initialized'] and live_start is None:
                live_start = model['produced']
                stages['first_raster_return'] = f
                print('FIRST_RASTER_RETURN', f, flush=True)
            if model is None and mb[0xdf] == 0xd6:
                stages['launch_request'] = f
                model = arm({'release': False}, 'startup')
                publish(model)
            elif model and not model['initialized'] and mb[0xf8] == 0xa5:
                model = arm({'release': True, 'input': list(mb[:5])}, 'startup')
                publish(model)
                last_service = f
            elif model and model['initialized'] and mb[0xf4] != last_consumed and f - last_service >= 8:
                bank = mb[0xfb]
                assert a.peek(0x8000, 16384) == published[bank]
                if cur == 9:
                    for pm in range(4):
                        assert a.peek(0x3204 + pm * 128, 96) == published[bank][0x3e00 + pm * 96:0x3e60 + pm * 96]
                # Screenshots show the currently selected real engine frame.
                if phase not in stages and phase != 'startup':
                    stages[phase] = f
                    (out / f'{phase}.png').write_bytes(a.screenshot())
                last_consumed = mb[0xf4]
                model = arm({'release': True, 'consume': True, 'input': list(mb[:5])}, phase)
                publish(model)
                last_service = f
            if live_start is not None and model['produced'] - live_start >= total:
                a.frame(3)
                a.regs()
                (out / 'gameplay.png').write_bytes(a.screenshot())
                break
        else:
            raise AssertionError('Gameplay did not complete')

        # The client proceeds immediately once each acknowledgement is ready.
        assert stages['first_raster_return'] - stages['launch_request'] < 20, stages
        for phase, menu_name in [('open_menu_hold', 'MainDef'), ('new_game_hold', 'EpiDef'),
                                 ('episode_hold', 'NewDef')]:
            samples = [t for t in trace if t['phase'] == phase]
            assert len(samples) >= 5, (phase, len(samples))
            assert all(t['menu'] == 1 and t['menuName'] == menu_name for t in samples), samples
            assert len({t['item'] for t in samples}) == 1, samples
        started = [t for t in trace if t['phase'] == 'difficulty_hold']
        # Doom defers ga_newgame until the next tic: the confirmation frame
        # can still contain the title after the menu has closed.
        assert len(started) == 8 and all(not t['menu'] for t in started), started
        assert all(t['state'] == 0 and not t['demo'] for t in started[1:]), started
        assert all(t['bullets'] == 50 for t in started if t['state'] == 0), 'Menu confirmation fired the weapon'
        levels = [t for t in trace if t['state'] == 0 and not t['menu'] and not t['demo']]
        assert len({(t.get('x'), t.get('y')) for t in levels}) > 5, 'No player movement'
        assert min(t['bullets'] for t in levels) < 50, 'No firing during play'
        keys = {(e['type'], e['key']) for e in events}
        assert (0, 13) not in keys and (0, 27) not in keys, 'START or SELECT was used to start'
        for key in [0x9d, 0xad, 0xae]:
            assert (0, key) in keys and (1, key) in keys, (key, keys)
        returns = int.from_bytes(a.peek(0x8a, 2), 'little')
        assert returns >= 400, returns
        controls()
        a.frame(3)
        a.regs()
        assert a.peek(0xd500, 2) == b'\0\0'
        controls(start=True, select=True, option=True)
        a.frame(3)
        a.regs()
        assert a.peek(0xd500, 2) == b'\x20\x03'
        controls()
        a.frame(3)
        a.regs()
        assert a.peek(0xd500, 2) == b'\0\0'
        # Failure reporting remains available, but never appears in healthy play.
        a.frame(2100)
        a.regs()
        timeout = a.peek(0x2900, 120).decode('ascii', 'replace')
        assert 'DOOM STOPPED' in timeout and 'NO NEW FRAME RECEIVED' in timeout, timeout
        result = {
            'version': '0.6.0', 'video_standard': args.tv, 'config': cfg,
            'emulator': 'Native AltirraSDL with ARM instruction model', 'os_crc32': '29f133f7',
            'car_sha256': hashlib.sha256(car.read_bytes()).hexdigest(),
            'engine_sha256': hashlib.sha256(args.engine.with_suffix('.bin').read_bytes()).hexdigest(),
            'startup_stages': stages, 'fire_only_start': True, 'held_fire_skips_menus': False,
            'held_start_fire_shoots_weapon': False, 'player_movement_verified': True,
            'bullets_before': 50, 'bullets_after': min(t['bullets'] for t in levels),
            'produced_frames': model['produced'], 'live_raster_returns': returns,
            'startup_text_removed': True, 'startup_pauses_removed': True,
            'frame_timeout_verified': True, 'audio_tested': False,
            'physical_or_dual_core_timing_tested': False,
        }
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print('RELEASE_CHECK_OK', json.dumps(result), flush=True)
        a.quit()
finally:
    if worker:
        if worker.poll() is None:
            worker.stdin.write('{"quit":true}\n')
            worker.stdin.flush()
        worker.stdin.close()
        try:
            worker.wait(10)
        except subprocess.TimeoutExpired:
            worker.terminate()
            worker.wait(5)
    if server.poll() is None:
        server.terminate()
    server.wait(5)
    log.close()
    engine_log.close()
