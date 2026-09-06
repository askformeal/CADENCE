from src import gen_response

def test_alive(ctx, request):
    return gen_response.Success('CADENCE backend is running')

def get_notifies(ctx, request):
    return gen_response.Success('Notifies got')

def exit_(ctx, request):
    ctx.exit_()
    return gen_response.Success('CADENCE backend is now exiting')