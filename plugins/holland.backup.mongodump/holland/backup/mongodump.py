import urllib
import logging
import subprocess

from pymongo import MongoClient

from holland.core.exceptions import BackupError

LOG = logging.getLogger(__name__)

# Specification for this plugin
# See: http://www.voidspace.org.uk/python/validate.html
CONFIGSPEC = """
[mongodump]
host = string(default=None)
username = string(default=None)
password = string(default=None)
authenticationDatabase = string(default=None)
""".splitlines()

class MongoDump(object):
    "MongoDB backup plugin for holland"

    def __init__(self, name, config, target_directory, dry_run=False):
        """Createa new MongoDump instance

        :param name: unique name of this backup
        :param config: dictionary config for this plugin
        :param target_directory: str path, under which backup data should be
                                 stored
        :param dry_run: boolean flag indicating whether this should be a real
                        backup run or whether this backup should only go
                        through the motions
        """
        self.name = name
        self.config = config
        self.target_directory = target_directory
        self.dry_run = dry_run
        LOG.info("Validating config")
        self.config.validate_config(CONFIGSPEC)

    def estimate_backup_size(self):
        """Estimate the size (in bytes) of the backup this plugin would
        produce, if run.

        :returns: int. size in bytes
        """
        ret = 0

        uri = "mongodb://"
        username = self.config["mongodump"].get("username")
        if username:
            uri += urllib.quote_plus(username)
            password = self.config["mongodump"].get("password")
            if password:
                uri += ":" + urllib.quote_plus(password)
            uri += '@'
        uri += self.config["mongodump"].get("host")
        client = MongoClient(uri)
        dbs = client.database_names()
        for db in dbs:
            c = client[db]
            tup = c.command("dbstats")
            ret += int(tup["storageSize"])
        # TODO: estimate, not just sum and divide by 2
        return ret / 2

    def backup(self):
        """
        Do what is necessary to perform and validate a successful backup.
        """
        command = ["mongodump"]
        username = self.config["mongodump"].get("username")
        if username:
            command += ["-u", username]
            password = self.config["mongodump"].get("password")
            if password:
                command += ["-p", password]
        command += ["--host", self.config["mongodump"].get("host")]
        command += ["--out", self.target_directory]

        if self.dry_run:
            LOG.info("[Dry run] MongoDump Plugin - test backup run")
            LOG.info("MongoDump command: %s" % subprocess.list2cmdline(command))
        else:
            LOG.info("Example plugin - real backup run")
            ret = subprocess.call(command)
            if ret != 0:
                raise BackupError("Mongodump returned %d" % ret)
            

    def info(self):
        """Provide extra information about the backup this plugin produced

        :returns: str. A textual string description the backup referenced by
                       `self.config`
        """
        return "MongoDB using mongodump plugin"
