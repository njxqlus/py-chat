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

    def __str__(self) -> str:
        return f"<{self.user}> {self.text}"

    def encode(self) -> bytes:
        return self.__str__().encode()

    def send(self, server: 'Server') -> None:
        encoded = self.encode()

        # отправка сообщения всем, кроме отправителя сообщения
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
                # присваиваю текущему пользователю логин
                self.user.login = login
                # приветствую пользователя
                self.transport.write(
                    f"Привет, {self.user}!\r\n".encode()
                )
                # отправляю пользователю посление сообщения
                self.send_history()

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
            # создаю объект сообщения
            message = Message(self.user, decoded)
            # добавляю сообщение в историю
            self.server.history.append(message)
            # отправляю сообщение
            message.send(self.server)

    def send_system_message(self, message):
        encoded = message.encode()

        self.transport.write(encoded)

    def send_history(self):
        # получаю последние сообщения с сервера (10 по умолчанию)
        last_messages = self.server.get_last_messages()
        if len(last_messages) > 0:
            # конвертирую в строку, чтобы не отправлять по одному сообщению
            last_messages_str = "Последние сообщения:"
            for item in last_messages:
                last_messages_str += f"\r\n{item}"
            # кодирую и отправляю сообщения
            self.transport.write(last_messages_str.encode())

    def connection_made(self, transport: transports.Transport):
        self.transport = transport
        self.server.clients.append(self)
        print("Соединение установлено")

    def connection_lost(self, exception):
        self.server.clients.remove(self)
        print("Соединение разорвано")


class Server:
    clients: list
    history: list

    def __init__(self):
        self.clients = []
        self.history = []

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

    def get_logged_in_users(self) -> list:
        logged_in_users = list()
        for client in self.clients:
            if client.user.login is not None:
                logged_in_users.append(client.user.login)
        return logged_in_users

    def get_last_messages(self, number=10) -> list:
        # если история пустая - возвращаю пустой список
        if len(self.history) == 0:
            return []
        # если история меньше, чем запрошенное кол-во сообщений, то уменьшаю запрошенное кол-во сообщение
        if len(self.history) < number:
            number = len(self.history)

        return self.history[-number:]


process = Server()
try:
    asyncio.run(process.start())
except KeyboardInterrupt:
    print("Сервер остановлен вручную")
