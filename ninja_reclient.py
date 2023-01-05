import ninja
import argparse
import subprocess
import sys
import os


def run(cmd_args):
  print(' '.join(cmd_args))
  subprocess.call(cmd_args)


def start_reproxy(reclient_cfg, reclient_bin_dir):
  run([
      os.path.join(reclient_bin_dir, 'bootstrap'), '--cfg=' + reclient_cfg,
      '--re_proxy=' + os.path.join(reclient_bin_dir, 'reproxy')
  ])


def stop_reproxy(reclient_cfg, reclient_bin_dir):
  run([
      os.path.join(reclient_bin_dir, 'bootstrap'),
      '--cfg=' + reclient_cfg,
      '--shutdown',
  ])


if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--reclient_cfg', type=str)
  parser.add_argument('--reclient_bin_dir', type=str)
  parser.add_argument('ninja_opts', nargs='*')
  args = parser.parse_args()
  try:
    start_reproxy(args.reclient_cfg, args.reclient_bin_dir)
    sys.exit(ninja.main([sys.argv[0]] + args.ninja_opts))
  except KeyboardInterrupt:
    stop_reproxy(args.reclient_cfg, args.reclient_bin_dir)
    sys.exit(1)
