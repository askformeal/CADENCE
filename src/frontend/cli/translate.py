def translate(args):
    if args['action'] == 'reload':
        args['action'] = 'load_last'

    return args