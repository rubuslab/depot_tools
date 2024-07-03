#!/usr/bin/env python3

import sys

import build_telemetry
import reclient_helper


def main(args):
    should_collect_logs = build_telemetry.load_config().enabled()

    use_reclient = None
    use_siso = None
    use_ninja = True
    if "use_reclient" in args:
        use_reclient = True
    if "use_siso" in args:
        use_siso = True
        use_ninja = False

    if use_reclient:
        with reclient_helper.build_context(["-C", "out/Default"], 'dummy',
                                           should_collect_logs) as ret_code:
            if use_siso:
                if should_collect_logs:
                    print("Uploading Siso logs")
                print("Run Siso build with Reclient")
            else:
                print("Run Ninja build with Reclient")
    else:
        if use_siso:
            if should_collect_logs:
                print("Uploading Siso logs")
            print("Run Siso build")
        else:
            print("Run Ninja build")

    if should_collect_logs:
        print("Uploading Ninja logs")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
