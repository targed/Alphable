import argparse
import sys

def main():
    parser = argparse.ArgumentParser(prog='alphable', description='Alphable V3 CLI')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Data
    data_parser = subparsers.add_parser('data', help='Data utilities')
    data_subparsers = data_parser.add_subparsers(dest='subcommand')
    data_subparsers.add_parser('prepare', help='Prepare dataset')

    # Train
    train_parser = subparsers.add_parser('train', help='Training utilities')
    train_subparsers = train_parser.add_subparsers(dest='subcommand')
    train_subparsers.add_parser('supervised', help='Supervised training')
    train_subparsers.add_parser('rl', help='Reinforcement learning training')
    train_subparsers.add_parser('rl-selfplay', help='Pure outcome self-play RL training', add_help=False)
    train_subparsers.add_parser('distill-macondo', help='Grandmaster Macondo knowledge distillation training', add_help=False)
    train_subparsers.add_parser('transformer-ranker', help='Fine-tune SmolLM2 Scrabble candidate ranker', add_help=False)

    # Selfplay
    selfplay_parser = subparsers.add_parser('selfplay', help='Selfplay utilities')
    selfplay_subparsers = selfplay_parser.add_subparsers(dest='subcommand')
    selfplay_subparsers.add_parser('generate', help='Generate selfplay games')

    # Eval
    eval_parser = subparsers.add_parser('eval', help='Evaluation utilities')
    eval_subparsers = eval_parser.add_subparsers(dest='subcommand')
    eval_subparsers.add_parser('matches', help='Evaluate matches')
    eval_subparsers.add_parser('baseline', help='Evaluate baseline')
    eval_subparsers.add_parser('plot', help='Plot training progress')

    # Pipeline
    pipeline_parser = subparsers.add_parser('pipeline', help='Pipeline utilities')
    pipeline_subparsers = pipeline_parser.add_subparsers(dest='subcommand')
    pipeline_subparsers.add_parser('calibrate', help='Run calibration cycle')

    # Search
    search_parser = subparsers.add_parser('search', help='Search utilities')
    search_subparsers = search_parser.add_subparsers(dest='subcommand')
    search_subparsers.add_parser('debug', help='Search debug')

    # Play
    play_parser = subparsers.add_parser('play', help='Play live on online platforms')
    play_subparsers = play_parser.add_subparsers(dest='subcommand')
    play_subparsers.add_parser('woogles', help='Play on Woogles.io', add_help=False)

    # We will pass the unparsed args to the actual module main functions
    args, unknown = parser.parse_known_args()

    if args.command == 'data' and args.subcommand == 'prepare':
        from alphable.training.prepare_dataset import main as prepare_dataset_main
        sys.argv = [sys.argv[0]] + unknown
        prepare_dataset_main()
    elif args.command == 'train' and args.subcommand == 'supervised':
        from alphable.training.train_supervised import main as train_supervised_main
        sys.argv = [sys.argv[0]] + unknown
        train_supervised_main()
    elif args.command == 'train' and args.subcommand == 'rl':
        from alphable.training.train_rl import main as train_rl_main
        sys.argv = [sys.argv[0]] + unknown
        train_rl_main()
    elif args.command == 'train' and args.subcommand == 'rl-selfplay':
        from alphable.training.self_play_rl import main as train_rl_selfplay_main
        sys.argv = [sys.argv[0]] + unknown
        train_rl_selfplay_main()
    elif args.command == 'train' and args.subcommand == 'distill-macondo':
        from alphable.training.distill_macondo import main as distill_macondo_main
        sys.argv = [sys.argv[0]] + unknown
        distill_macondo_main()
    elif args.command == 'train' and args.subcommand == 'transformer-ranker':
        from alphable.training.train_transformer_ranker import main as train_transformer_ranker_main
        sys.argv = [sys.argv[0]] + unknown
        train_transformer_ranker_main()
    elif args.command == 'selfplay' and args.subcommand == 'generate':
        from alphable.training.self_play import main as self_play_main
        sys.argv = [sys.argv[0]] + unknown
        self_play_main()
    elif args.command == 'eval' and args.subcommand == 'matches':
        from alphable.eval.evaluate_matches import main as evaluate_matches_main
        sys.argv = [sys.argv[0]] + unknown
        evaluate_matches_main()
    elif args.command == 'eval' and args.subcommand == 'baseline':
        from alphable.eval.evaluate_vs_baseline import main as evaluate_vs_baseline_main
        sys.argv = [sys.argv[0]] + unknown
        evaluate_vs_baseline_main()
    elif args.command == 'eval' and args.subcommand == 'plot':
        from alphable.eval.analyze import main as analyze_main
        sys.argv = [sys.argv[0]] + unknown
        analyze_main()
    elif args.command == 'pipeline' and args.subcommand == 'calibrate':
        from alphable.pipeline.calibration_cycle import main as calibration_cycle_main
        sys.argv = [sys.argv[0]] + unknown
        calibration_cycle_main()
    elif args.command == 'search' and args.subcommand == 'debug':
        from alphable.core.search import main as search_debug_main
        sys.argv = [sys.argv[0]] + unknown
        search_debug_main()
    elif args.command == 'play' and args.subcommand == 'woogles':
        from alphable.platform.cli import main as play_woogles_main
        sys.argv = [sys.argv[0]] + unknown
        play_woogles_main()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
