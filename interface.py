import objectsharer as objsh

def plotwindow_client(serveraddr='127.0.0.1', serverport=55557, localaddr='127.0.0.1'):
    zbe = objsh.ZMQBackend()
    zbe.start_server(addr=localaddr)
    zbe.refresh_connection('tcp://%s:%d' % (serveraddr, serverport))     # Data server
    return objsh.helper.find_object('plotwin')
