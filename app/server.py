"""
Серверное приложение для соединений
"""
import asyncio
from asyncio import transports


class User:
    login: str or None

    def __init__(self, login=None):
        self.login = login

    def __str__(self):
        return self.login


class Message:
    text: str
    user: 'User'

    def __init__(self, user: User, text: str):
        self.user = user
        self.text = text

    def __str__(self):
        return f"<{self.user}> {self.text}"

    def encode(self):
        return self.__str__().encode()

    def send(self, server: 'Server'):
        encoded = self.encode()

        for client in server.clients:
            if client.user != self.user:
                client.transport.write(encoded)


class ClientProtocol(asyncio.Protocol):
    user: 'User'
    server: 'Server'
    transport: transports.Transport

    def __init__(self, server: 'Server'):
        self.server = server
        self.user = User()

    def data_received(self, data: bytes):
        decoded = data.decode()
        print(decoded)

        # Проверям, залогинен ли пользователь
        if self.user.login is None:
            # если строка сообщения начинается с login: - пытаемся авторизовать его
            # todo проверять, есть ли что-то после слова login:
            if decoded.startswith("login:"):
                self.user.login = decoded.replace("login:", "").replace("\r\n", "")
                # todo проверять, нет ли уже пользователя с таким логином онлайн
                self.transport.write(
                    f"Привет, {self.user}!".encode()
                )
            # если нет - отправляем данному пользователю ошибку
            else:
                self.send_error("Для того, чтобы отправлять сообщения, вам необходимо войти в чат. Для этого напишите "
                                "login:User, где User - ваш логин")
        else:
            message = Message(self.user, decoded)
            message.send(server=self.server)

    def send_error(self, error):
        encoded = error.encode()

        for client in self.server.clients:
            if client.user == self.user:
                client.transport.write(encoded)

    def connection_made(self, transport: transports.Transport):
        self.transport = transport
        self.server.clients.append(self)
        print("Соединение установлено")

    def connection_lost(self, exception):
        self.server.clients.remove(self)
        print("Соединение разорвано")


class Server:
    clients: list

    def __init__(self):
        self.clients = []

    def create_protocol(self):
        return ClientProtocol(self)

    async def start(self):
        loop = asyncio.get_running_loop()

        coroutine = await loop.create_server(
            self.create_protocol,
            "127.0.0.1",
            8888
        )

        print("Сервер запущен ...")

        await coroutine.serve_forever()


process = Server()
try:
    asyncio.run(process.start())
except KeyboardInterrupt:
    print("Сервер остановлен вручную")
