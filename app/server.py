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

        # команда для вывода пользователей онлайн
        if decoded == "online":
            self.send_system_message(", ".join(self.server.get_logged_in_users()))

        # пользователь пытается залогинится и он дейсвительно еще не залогинен
        elif decoded.startswith("login:") and self.user.login is None:
            login = decoded.replace("login:", "").replace("\r\n", "")
            # проверяем, нет ли пользователей с таким логином онлайн. если есть - рвем соединение
            if self.server.is_client_online(login):
                self.send_system_message(
                    f"Логин {login} занят, попробуйте другой"
                )
                # закрывает транспорт, согласно документации он вызывает connection_lost()
                self.transport.close()
            # если нет - логиним и привествуем пользователя
            else:
                self.user.login = login
                self.transport.write(
                    f"Привет, {self.user}!".encode()
                )

        # пользователь пытается залогиниться, но он уже залогинен
        elif decoded.startswith("login:") and self.user.login is not None:
            self.send_system_message(
                f"Вы уже вошли под пользователем {self.user}. Если хотите перезайти - перезапустите программу"
            )

        # пользователя еще не залогинен и не пытается
        elif not decoded.startswith("login:") and self.user.login is None:
            self.send_system_message(
                "Для отправки сообщений вам необходимо войти. Используйте команду login:Name, где Name - ваше имя"
            )

        # пользователь залогинен и отправляет сообщение
        else:
            message = Message(self.user, decoded)
            message.send(self.server)

    def send_system_message(self, error):
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

    def is_client_online(self, login: str) -> bool:
        for client in self.clients:
            if login == client.user.login:
                return True
        return False

    def get_logged_in_users(self):
        logged_in_users = list()
        for client in self.clients:
            if client.user.login is not None:
                logged_in_users.append(client.user.login)
        return logged_in_users


process = Server()
try:
    asyncio.run(process.start())
except KeyboardInterrupt:
    print("Сервер остановлен вручную")
