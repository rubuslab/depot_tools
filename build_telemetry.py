import textwrap

COLOR_NOTICE = '\033[33m' # Yellow
COLOR_END = '\033[0m'

def print_notice():
    msg = textwrap.dedent(f"""\
    {COLOR_NOTICE}Build telemetry (including build data, email address, and hostname) is collected on Google corp machines to understand performance and diagnose build issues. You can run `build_telemetry [--opt-in] [--opt-out]` to suppress this message. See go/chrome-dev-build-telemetry for details.
    {COLOR_END}""")
    print(msg)
