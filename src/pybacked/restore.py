import csv
import hashlib
import io
import os
import pybacked
import pybacked.diff
import pybacked.zip_handler
import zipfile


def find_diff(logfile, filename):
    """
    Find a diff-log occurance in a file. If one exists return the diff line.
    If the filename given is not found return 0.

    :param logfile: the csv log-file to be searched
    :param filename: the name of the desired file
    :return: the diff-entry or None depending if filename was found
    :rtype: dict
    """
    csv_reader = csv.DictReader(logfile, delimiter=',')
    for entry in csv_reader:
        if entry["filename"] == filename:
            return entry
    else:
        return None


def find_diff_archive(archivepath, filename):
    """
    Find a diff-log occurance in an archive. If one exists return the diff
    line. If the filename given is not found return 0.

    :param archivepath: The path of the archive
    :param filename: The name of the desired file
    :return: the diff-entry or None depending if filename was found
    :rtype: dict
    """
    # This function eccentialy just opens the log-file inside the archive
    # and wrapps it in a way that find_diff can understand
    archive = zipfile.ZipFile(archivepath, mode='r')
    diff_log_bytes = archive.open("diff-log.csv", mode='r')
    diff_log = io.TextIOWrapper(diff_log_bytes, encoding="UTF-8", newline=None)

    diff_entry = find_diff(diff_log, filename)

    diff_log_bytes.close()
    archive.close()

    return diff_entry


def get_archive_list(archivedir):
    """
    Return a list of paths to all the backup archives.

    :param archivedir: The directory in which archives are stored
    :return: a list of paths to all the backup archives
    :rtype: list
    """
    raw_list = os.listdir(archivedir)
    final_list = []
    for member in raw_list:
        if os.path.isfile(os.path.abspath(archivedir + '/' + member)):
            if member.find(".zip") > -1:
                final_list.append(os.path.abspath(archivedir + '/' + member))
    # invert order to have newest archive on [0]
    final_list.sort(reverse=True)
    return final_list


def get_current_state(filepath, diff_algorithm, hash_algorithm=None):
    """
    Get the current state of the file.

    :param filepath: the path to the file
    :type filepath: str
    :param diff_algorithm: the diff algorithm used
    :type diff_algorithm: int
    :param hash_algorithm: the desired hash algorithm
    :type hash_algorithm: str, optional
    :return: return the current state, or None if file doesn't exist
    """
    if os.path.isfile(filepath) is False:
        return None

    if diff_algorithm == pybacked.DIFF_HASH and hash_algorithm is None:
        raise ValueError("No hash algorithm selected")
    if diff_algorithm == pybacked.DIFF_DATE:
        return get_edit_date(filepath)
    elif diff_algorithm == pybacked.DIFF_HASH:
        return get_file_hash(filepath, hash_algorithm)
    elif diff_algorithm == pybacked.DIFF_CONT:
        return get_file_content(filepath)


def get_file_hash(filepath, algorithm):
    """
    Get hash of a file.

    :param filepath: the path to the file
    :type filepath: str
    :param algorithm: the desired hashing algorithm
    :type algorithm: str
    :return: Hash of the file in hex form.
    :rtype: str
    """
    file = io.open(filepath, "rb")
    hash_handler = hashlib.new(algorithm)
    hash_handler.update(file.read())
    file.close()
    return hash_handler.hexdigest()


def get_edit_date(filepath):
    """
    Return the unix timestamp for the last edit. This function is primarily
    implemented for increasing readability.

    :param filepath: the filename
    :return: timestamp of the last edited date
    :rtype: float
    """
    timestamp = os.path.getmtime(filepath)
    return timestamp


def get_file_content(filepath):
    """
    Get the file content in binary mode

    :param filepath: The path to the file
    :type filepath: str
    :return: The content of the file
    :rtype: bytes
    """
    file = open(filepath, "rb")
    content = file.read()
    file.close()
    return content


def get_arch_state(filename, archivedir, diff_algorithm):
    """
    Get the last (diff) state of the archived file version.

    :param filename: The filename searched for
    :type filename: str
    :param archivedir: The directory where the archive files are stored
    :type archivedir: str
    :param diff_algorithm: The diff-detection algorithm used
    :type diff_algorithm: int
    :return: the last state (diff) of the archived file
    """
    archive_list = get_archive_list(archivedir)
    i = 0
    i_max = len(archive_list)
    diff_entry = None
    while diff_entry is None:
        if i == i_max:
            break
        diff_entry = find_diff_archive(archive_list[i], filename)
        i += 1
    if diff_entry is None:
        return None
    else:
        if diff_algorithm == pybacked.DIFF_DATE:
            return float(diff_entry['diff'])
        elif diff_algorithm == pybacked.DIFF_HASH:
            return diff_entry['diff']
        elif diff_algorithm == pybacked.DIFF_CONT:
            return bytes.fromhex(diff_entry['diff'])


def restore(config, archname, alt_dir=None):
    """
    Restore a given backup to the original source directory or an alternative
    directory.

    :param config: The configuration for the backup
    :type config: Configuration
    :param archname: The name of the archive which holds the state which should
        be restored.
    :type archname: str
    :param alt_dir: Specifies an alternate directory in which the source will
        be restored. If this is None, the function will restore the source
        to the original source directory specified in the provieded
        Configuration class instance.
    :type alt_dir: str, optional
    :return: void
    :rtype: None
    """
    if alt_dir is None:
        restore_dir = config.storage
    else:
        restore_dir = alt_dir
    archive = os.path.abspath(config.archive + "/" + archname)
    restore_archive_state(archive, restore_dir)


def restore_archive_state(archive, restore_dir):
    """
    Restore a given archive state. This will restore the state of the source
    at the creation of the specified archive.

    :param archive: The path to the specific zip-archive with the state that is
        to be restored
    :type archive: str
    :param restore_dir: The directory in which the archive should be restored
    :type restore_dir: str
    :return: void
    :rtype: None
    """
    archive_dir = os.path.split(archive)[0]
    archive_list = get_archive_list(archive_dir)
    # put archives into ascending order
    archive_list.sort()
    index = archive_list.index(archive)
    for i in range(index + 1):
        diffcache = pybacked.diff.diff_log_deserialize(archive_list[i],
                                                       basepath=None)
        for entry in diffcache:
            archname = "data/" + entry[0]
            destination = os.path.abspath(restore_dir + "/" + entry[0])
            if entry[1].difftype == '+':
                pybacked.zip_handler.extract_archdata(archive_list[i],
                                                      archname, destination)
            elif entry[1].difftype == '*':
                if os.path.exists(destination):
                    os.remove(destination)
                pybacked.zip_handler.extract_archdata(archive_list[i],
                                                      archname, destination)
            elif entry[1].difftype == '-':
                if os.path.exists(destination):
                    os.remove(destination)
