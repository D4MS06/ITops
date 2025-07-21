# monitoring/utils/exceptions.py

class DeviceReadingError(Exception):
    """Exception levée lors d’un problème de lecture/écriture JSON."""
    pass