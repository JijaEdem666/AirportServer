from service.ServiceHost import ServiceHost

host = ServiceHost()
app = host.app

if __name__ == "__main__":
    host.start()