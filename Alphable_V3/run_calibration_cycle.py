import argparse
import datetime
import json
import os
import subprocess
import sys
import time


def run_and_tee(command, cwd, log_path, env=None):
    start = time.time()
    with open(log_path, 'w', encoding='utf-8') as log_file:
        log_file.write(f"$ {' '.join(command)}\n\n")
        log_file.flush()

        proc = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )

        assert proc.stdout is not None
        for line in proc.stdout:
            sys.stdout.write(line)
            log_file.write(line)

        proc.wait()

    duration = time.time() - start
    return proc.returncode, duration


def build_commands(args):
    cmds = []

    self_play_cmd = [
        args.python,
        'self_play.py',
        '--games', str(args.games),
        '--output', args.rl_data,
        '--top-k', str(args.selfplay_top_k),
        '--temperature', str(args.selfplay_temperature),
        '--infer-batch-size', str(args.infer_batch_size),
    ]
    if args.append:
        self_play_cmd.append('--append')
    cmds.append(('self_play', self_play_cmd))

    train_cmd = [
        args.python,
        'train_rl.py',
        '--data', args.rl_data,
        '--init-model', args.init_model,
        '--save-model', args.rl_model,
        '--batch-size', str(args.batch_size),
        '--lr', str(args.lr),
        '--weight-decay', str(args.weight_decay),
        '--epochs', str(args.epochs),
        '--train-split', str(args.train_split),
        '--early-stop', str(args.early_stop),
    ]
    cmds.append(('train_rl', train_cmd))

    eval_cmd = [
        args.python,
        'evaluate_matches.py',
        '--model-a', args.bc_model,
        '--model-b', args.rl_model,
        '--games', str(args.eval_games),
        '--infer-batch-size', str(args.infer_batch_size),
    ]
    cmds.append(('evaluate', eval_cmd))

    return cmds


def main():
    parser = argparse.ArgumentParser(
        description='Run one full RL calibration cycle with live and saved logs.'
    )
    parser.add_argument('--workspace', default='.',
                        help='Workspace root containing project scripts.')
    parser.add_argument('--python', default=sys.executable,
                        help='Python executable to use.')

    parser.add_argument('--games', type=int, default=1000,
                        help='Self-play games this cycle.')
    parser.add_argument('--append', dest='append', action='store_true',
                        help='Append to RL dataset (default behavior).')
    parser.add_argument('--overwrite', dest='append', action='store_false',
                        help='Overwrite RL dataset before self-play step.')
    parser.set_defaults(append=True)
    parser.add_argument(
        '--rl-data', default='data/rl/rl_samples.jsonl', help='RL dataset path.')
    parser.add_argument('--selfplay-top-k', type=int, default=5)
    parser.add_argument('--selfplay-temperature', type=float, default=0.20)

    parser.add_argument(
        '--init-model', default='models/alphable_rl_best_val_model.pth')
    parser.add_argument(
        '--rl-model', default='models/alphable_rl_best_val_model.pth')
    parser.add_argument(
        '--bc-model', default='models/alphable_best_val_model.pth')
    parser.add_argument('--batch-size', type=int, default=128)
    parser.add_argument('--lr', type=float, default=5e-4)
    parser.add_argument('--weight-decay', type=float, default=1e-4)
    parser.add_argument('--epochs', type=int, default=20)
    parser.add_argument('--train-split', type=float, default=0.9)
    parser.add_argument('--early-stop', type=int, default=4)

    parser.add_argument('--eval-games', type=int, default=200)
    parser.add_argument('--infer-batch-size', type=int, default=128)

    parser.add_argument(
        '--logs-dir', default='logs/calibration_runs', help='Directory for run logs.')
    args = parser.parse_args()

    workspace = os.path.abspath(args.workspace)
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    run_dir = os.path.join(workspace, args.logs_dir, timestamp)
    os.makedirs(run_dir, exist_ok=True)

    print('Starting calibration cycle...')
    print(f'Workspace: {workspace}')
    print(f'Run logs: {run_dir}')

    commands = build_commands(args)
    summary = {
        'timestamp': timestamp,
        'workspace': workspace,
        'steps': [],
    }

    for step_name, cmd in commands:
        log_path = os.path.join(run_dir, f'{step_name}.log')
        print(f"\n=== [{step_name}] ===")
        print('$ ' + ' '.join(cmd))

        rc, seconds = run_and_tee(cmd, cwd=workspace, log_path=log_path)
        summary['steps'].append({
            'step': step_name,
            'command': cmd,
            'return_code': rc,
            'seconds': round(seconds, 2),
            'log': os.path.relpath(log_path, workspace),
        })

        if rc != 0:
            print(f"Step '{step_name}' failed with exit code {rc}.")
            break

    summary['success'] = all(s['return_code'] == 0 for s in summary['steps'])
    summary_path = os.path.join(run_dir, 'summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    print('\nCalibration cycle complete.')
    print(f"Success: {summary['success']}")
    print(f"Summary: {os.path.relpath(summary_path, workspace)}")

    if not summary['success']:
        sys.exit(1)


if __name__ == '__main__':
    main()
