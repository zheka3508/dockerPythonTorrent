"""
Клиент для работы с Transmission RPC API
"""
import logging
from io import BytesIO
from transmission_rpc import Client
from transmission_rpc.error import TransmissionError

logger = logging.getLogger(__name__)


class TransmissionClient:
    """Обертка над transmission-rpc для удобной работы"""
    
    def __init__(self, host, port, username, password, path='/transmission/rpc'):
        """
        Инициализация клиента Transmission
        
        Args:
            host: Адрес хоста Transmission
            port: Порт RPC (обычно 9091)
            username: Имя пользователя
            password: Пароль
            path: Путь к RPC endpoint
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.path = path
        self._client = None
        self._connect()
    
    def _connect(self):
        """Установка соединения с Transmission"""
        try:
            self._client = Client(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                path=self.path
            )
            logger.info(f"Подключено к Transmission на {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Ошибка подключения к Transmission: {e}")
            raise
    
    def _ensure_connection(self):
        """Проверка и переподключение при необходимости"""
        if self._client is None:
            self._connect()
    
    def add_torrent(self, torrent_data):
        """
        Добавить торрент в Transmission
        
        Args:
            torrent_data: BytesIO объект с данными .torrent файла
            
        Returns:
            Объект торрента
        """
        self._ensure_connection()
        
        try:
            # Переводим BytesIO в байты
            if isinstance(torrent_data, BytesIO):
                torrent_bytes = torrent_data.read()
            else:
                torrent_bytes = torrent_data
            
            # Добавляем торрент
            torrent = self._client.add_torrent(torrent_bytes, paused=False)
            logger.info(f"Торрент добавлен: {torrent.name}")
            return torrent
            
        except TransmissionError as e:
            logger.error(f"Ошибка Transmission при добавлении торрента: {e}")
            raise
        except Exception as e:
            logger.error(f"Ошибка при добавлении торрента: {e}")
            raise
    
    def get_all_torrents(self):
        """
        Получить все торренты
        
        Returns:
            Список всех торрентов
        """
        self._ensure_connection()
        
        try:
            torrents = self._client.get_torrents()
            return torrents
        except TransmissionError as e:
            logger.error(f"Ошибка Transmission при получении торрентов: {e}")
            raise
        except Exception as e:
            logger.error(f"Ошибка при получении торрентов: {e}")
            raise
    
    def get_active_torrents(self):
        """
        Получить только активные торренты (загружающиеся или раздающиеся)
        
        Returns:
            Список активных торрентов
        """
        self._ensure_connection()
        
        try:
            all_torrents = self._client.get_torrents()
            # Активные статусы: downloading, seeding, check, check_wait, download_wait, seed_wait
            active_statuses = ['downloading', 'seeding', 'check', 'check_wait', 'download_wait', 'seed_wait', 'download_pending']
            active_torrents = [
                t for t in all_torrents 
                if t.status in active_statuses
            ]
            return active_torrents
        except TransmissionError as e:
            logger.error(f"Ошибка Transmission при получении активных торрентов: {e}")
            raise
        except Exception as e:
            logger.error(f"Ошибка при получении активных торрентов: {e}")
            raise
    
    def pause_all(self):
        """
        Поставить все торренты на паузу
        
        Returns:
            Количество остановленных торрентов
        """
        self._ensure_connection()
        
        try:
            torrents = self._client.get_torrents()
            # Собираем ID торрентов, которые не остановлены
            torrent_ids = [t.id for t in torrents if t.status != 'stopped']
            
            if torrent_ids:
                # Останавливаем все торренты одним вызовом
                self._client.stop_torrent(torrent_ids)
            
            count = len(torrent_ids)
            logger.info(f"Остановлено торрентов: {count}")
            return count
        except TransmissionError as e:
            logger.error(f"Ошибка Transmission при остановке торрентов: {e}")
            raise
        except Exception as e:
            logger.error(f"Ошибка при остановке торрентов: {e}")
            raise
    
    def resume_all(self):
        """
        Продолжить все торренты, которые не были загружены до конца
        
        Returns:
            Количество продолженных торрентов
        """
        self._ensure_connection()
        
        try:
            torrents = self._client.get_torrents()
            # Собираем ID остановленных торрентов, которые не загружены на 100%
            torrent_ids = [
                t.id for t in torrents 
                if t.status == 'stopped' and t.percent_done < 1.0
            ]
            
            if torrent_ids:
                # Запускаем все торренты одним вызовом
                self._client.start_torrent(torrent_ids)
            
            count = len(torrent_ids)
            logger.info(f"Продолжено торрентов: {count}")
            return count
        except TransmissionError as e:
            logger.error(f"Ошибка Transmission при продолжении торрентов: {e}")
            raise
        except Exception as e:
            logger.error(f"Ошибка при продолжении торрентов: {e}")
            raise

