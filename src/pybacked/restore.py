import csv
import io
import os
import pybacked
import zipfile


def find_diff(logfile, filename):
    """
    Find a diff-log occurance in a file. If one exists return the diff line.
    If the filename given is not found return 0
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
    line. If the filename given is not found return 0
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
    :param archivedir:
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


def get_last_state(filename, archivedir, diff_algorithm):
    """
    Get the last (diff) state of the archived file version
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
