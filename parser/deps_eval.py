import cStringIO
import grammar
import pprint
import sys
import tokenize


_DEFAULT_TEST = """\
# Big block of copyright comments
# Lorem ipsum dolor sit amet, consectetur adipiscing elit. Praesent vitae felis
# luctus, lobortis diam in, bibendum magna. Sed eget lacus quis magna dignissim
# feugiat ut sed metus. Quisque in diam eget turpis congue imperdiet. Morbi
# ultrices vitae tellus id faucibus. Etiam aliquet ultricies massa. Praesent sed
# mi odio. Suspendisse sodales purus id nunc tristique gravida. Donec laoreet
# accumsan lorem, sit amet convallis lectus mollis in. Nulla at purus pharetra,
# cursus quam suscipit, facilisis odio.

vars = {
  # Some comment
  'chromium_git': 'https://chromium.googlesource.com',
  # Three lines of comments
  # Lorem ipsum dolor sit amet, consectetur adipiscing elit. Praesent vitae
  # felis luctus, lobortis diam in, bibendum magna. Sed eget lacus quis magna
  'webrtc_git': 'https://webrtc.googlesource.com',
  # Three lines of comments
  # Lorem ipsum dolor sit amet, consectetur adipiscing elit. Praesent vitae
  # felis luctus, lobortis diam in, bibendum magna. Sed eget lacus quis magna
  'webrtc_rev': 'deadbeef',
  # Three lines of comments
  # Lorem ipsum dolor sit amet, consectetur adipiscing elit. Praesent vitae
  # felis luctus, lobortis diam in, bibendum magna. Sed eget lacus quis magna
}
deps = {
  'src/v8': Var('chromium_git') + '/v8/v8.git' + '@' + 'c092edb',

  # comment
  'src/third_party/lighttpd': {
    'url': Var('chromium_git') + '/deps/lighttpd.git' + '@' + '9dfa55d',
    'condition': 'checkout_mac or checkout_win',
  },
  'src/third_party/webrtc': {
    'url': '{webrtc_git}/src.git',
    'revision': '{webrtc_rev}',
  },
  'src/third_party/intellij': {
    'packages': [{
      'package': 'chromium/third_party/intellij', # comment
      'version': 'version:12.0-cr0',
    }],
    'condition': 'checkout_android',
    'dep_type': 'cipd',
  },
}
deps_os = {
  'win': {
    'src/third_party/cygwin':
      Var('chromium_git') + '/chromium/deps/cygwin.git' + '@' + 'c89e446',
  }
}
hooks = [
  {
    # This clobbers when necessary (based on get_landmines.py). It must be the
    # first hook so that other things that get/generate into the output
    # directory will not subsequently be clobbered.
    'name': 'landmines',
    'pattern': '.',
    'action': [
        'python',
        'src/build/landmines.py'
    ],
  },
  {
    # Ensure that the DEPS'd "depot_tools" has its self-update capability
    # disabled.
    'name': 'disable_depot_tools_selfupdate',
    'pattern': '.',
    'action': [
        'python',
        'src/third_party/depot_tools/update_depot_tools_toggle.py',
        '--disable',
    ]
  },
  {
    # Ensure that we don't accidentally reference any .pyc files whose
    # corresponding .py files have since been deleted.
    # We could actually try to avoid generating .pyc files, crbug.com/500078.
    'name': 'remove_stale_pyc_files',
    'pattern': '.',
    'action': [
        'python',
        'src/tools/remove_stale_pyc_files.py',
        'src/android_webview/tools',
        'src/build/android',
        'src/gpu/gles2_conform_support',
        'src/infra',
        'src/ppapi',
        'src/printing',
        'src/third_party/blink/tools',  # See http://crbug.com/625877.
        'src/third_party/catapult',
        'src/third_party/closure_compiler/build',
        'src/third_party/WebKit/Tools/Scripts',  # See http://crbug.com/625877.
        'src/tools',
    ],
  },
]
"""

def _GenerateTokens(contents):
  return [
      token
      for token in tokenize.generate_tokens(
          cStringIO.StringIO(contents).readline)
      if token[0] not in {tokenize.NEWLINE, tokenize.NL}
  ]

def Parse(contents):
  ctx = grammar.GetPythonLikeContext()
  ctx.transform = True

  tokens = _GenerateTokens(contents)
  return ctx.Parse(tokens)

def main():
  if len(sys.argv) < 2:
    test = _DEFAULT_TEST
  else:
    test = open(sys.argv[1]).read()

  result, _, err = Parse(test)
  if err:
    print '\n'.join(err)
  else:
    pprint.pprint(result)

if __name__ == '__main__':
  sys.exit(main())
