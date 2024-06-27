abandon
        data = f.read()
    result = gerrit_util.ChangeEdit(
        urllib.parse.urlparse(opt.host).netloc, opt.change, opt.path, data)
    logging.info(result)
    write_result(result, opt)


@subcommand.usage('[args ...]')
def CMDpublishchangeedit(parser, args):
    """Publish a Gerrit change edit."""
    parser.add_option('-c', '--change', type=int, help='change number')
    parser.add_option('--notify', help='whether to notify')

    (opt, args) = parser.parse_args(args)

    result = gerrit_util.PublishChangeEdit(
        urllib.parse.urlparse(opt.host).netloc, opt.change, opt.notify)
    logging.info(result)
    write_result(result, opt)


@subcommand.usage('[args ...]')
def CMDsubmitchange(parser, args):
    """Submit a Gerrit change."""
    parser.add_option('-c', '--change', type=int, help='change number')
    (opt, args) = parser.parse_args(args)
    result = gerrit_util.SubmitChange(
        urllib.parse.urlparse(opt.host).netloc, opt.change)
    logging.info(result)
    write_result(result, opt)


@subcommand.usage('[args ...]')
def CMDchangesubmittedtogether(parser, args):
    """Get all changes submitted with the given one."""
    parser.add_option('-c', '--change', type=int, help='change number')
    (opt, args) = parser.parse_args(args)
    result = gerrit_util.GetChangesSubmittedTogether(
        urllib.parse.urlparse(opt.host).netloc, opt.change)
    logging.info(result)
    write_result(result, opt)


@subcommand.usage('[args ...]')
def CMDgetcommitincludedin(parser, args):
    """Retrieves the branches and tags for a given commit."""
    parser.add_option('--commit', dest='commit', help='commit hash')
    (opt, args) = parser.parse_args(args)
    result = gerrit_util.GetCommitIncludedIn(
        urllib.parse.urlparse(opt.host).netloc, opt.project, opt.commit)
    logging.info(result)
    write_result(result, opt)


@subcommand.usage('[args ...]')
def CMDsetbotcommit(parser, args):
    """Sets bot-commit+1 to a bot generated change."""
    parser.add_option('-c', '--change', type=int, help='change number')
    (opt, args) = parser.parse_args(args)
    result = gerrit_util.SetReview(urllib.parse.urlparse(opt.host).netloc,
                                   opt.change,
                                   labels={'Bot-Commit': 1},
                                   ready=True)
    logging.info(result)
    write_result(result, opt)


@subcommand.usage('[args ...]')
def CMDsetlabel(parser, args):
    """Sets a label to a specific value on a given change."""
    parser.add_option('-c', '--change', type=int, help='change number')
    parser.add_option('-l',
                      '--label',
                      nargs=2,
                      metavar=('label_name', 'label_value'))
    (opt, args) = parser.parse_args(args)
    result = gerrit_util.SetReview(urllib.parse.urlparse(opt.host).netloc,
                                   opt.change,
                                   labels={opt.label[0]: opt.label[1]})
    logging.info(result)
    write_result(result, opt)


@subcommand.usage('')
def CMDabandon(parser, args):
    """Abandons a Gerrit change."""
    parser.add_option('-c', '--change', type=int, help='change number')
    parser.add_option('-m',
                      '--message',
                      default='',
                      help='reason for abandoning')

    (opt, args) = parser.parse_args(args)
    assert opt.change, "-c not defined"
    result = gerrit_util.AbandonChange(
        urllib.parse.urlparse(opt.host).netloc, opt.change, opt.message)
    logging.info(result)
    write_result(result, opt)


@subcommand.usage('')
def CMDmass_abandon(parser, args):
    """Mass abandon changes

    Abandons CLs that match search criteria provided by user. Before any change
    is actually abandoned, user is presented with a list of CLs that will be
    affected if user confirms. User can skip confirmation by passing --force
    parameter.

    The script can abandon up to 100 CLs per invocation.

    Examples:
    gerrit_client.py mass-abandon --host https://HOST -p 'project=repo2'
    gerrit_client.py mass-abandon --host https://HOST -p 'message=testing'
    gerrit_client.py mass-abandon --host https://HOST -p 'is=wip' -p 'age=1y'
    """
    parser.add_option('-p',
                      '--param',
                      dest='params',
                      action='append',
                      default=[],
                      help='repeatable query parameter, format: -p key=value')
    parser.add_option('-m',
                      '--message',
                      default='',
                      help='reason for abandoning')
    parser.add_option('-f',
                      '--force',
                      action='store_true',
                      help='Don\'t prompt for confirmation')

    opt, args = parser.parse_args(args)

    for p in opt.params:
        assert '=' in p, '--param is key=value, not "%s"' % p
    search_query = list(tuple(p.split('=', 1)) for p in opt.params)
    if not any(t for t in search_query if t[0] == 'owner'):
        # owner should always be present when abandoning changes
        search_query.append(('owner', 'me'))
    search_query.append(('status', 'open'))
    logging.info("Searching for: %s" % search_query)

    host = urllib.parse.urlparse(opt.host).netloc

    result = gerrit_util.QueryChanges(
        host,
        search_query,
        # abandon at most 100 changes as not all Gerrit instances support
        # unlimited results.
        limit=100,
    )
    if len(result) == 0:
        logging.warning("Nothing to abandon")
        return

    logging.warning("%s CLs match search query: " % len(result))
    for change in result:
        logging.warning("[ID: %d] %s" % (change['_number'], change['subject']))

    if not opt.force:
        q = input('Do you want to move forward with abandoning? [y to confirm] '
                  ).strip()
        if q not in ['y', 'Y']:
            logging.warning("Aborting...")
            return

    for change in result:
        logging.warning("Abandoning: %s" % change['subject'])
        gerrit_util.AbandonChange(host, change['id'], opt.message)

    logging.warning("Done")


class OptionParser(optparse.OptionParser):
    """Creates the option parse and add --verbose support."""
    def __init__(self, *args, **kwargs):
        optparse.OptionParser.__init__(self,
                                       *args,
                                       version=__version__,
                                       **kwargs)
        self.add_option('--verbose',
                        action='count',
                        default=0,
                        help='Use 2 times for more debugging info')
        self.add_option('--host', dest='host', help='Url of host.')
        self.add_option('--project', dest='project', help='project name')
        self.add_option('--json_file',
                        dest='json_file',
                        help='output json filepath')

    def parse_args(self, args=None, values=None):
        options, args = optparse.OptionParser.parse_args(self, args, values)
        # Host is always required
        assert options.host, "--host not defined."
        levels = [logging.WARNING, logging.INFO, logging.DEBUG]
        logging.basicConfig(level=levels[min(options.verbose, len(levels) - 1)])
        return options, args


def main(argv):
    dispatcher = subcommand.CommandDispatcher(__name__)
    return dispatcher.execute(OptionParser(), argv)


if __name__ == '__main__':
    # These affect sys.stdout so do it outside of main() to simplify mocks in
    # unit testing.
    setup_color.init()
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.stderr.write('interrupted\n')
        sys.exit(1)
