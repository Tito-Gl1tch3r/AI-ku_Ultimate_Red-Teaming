# You will not be able to run this file here and will need to copy it onto your computer and run it on your machine.
# You will also need to make sure you have installed the requests module from PyPi (pip install)
# This file won't run unless the main file[see line 73] and @NOTE at the end

import requests
import hashlib
import sys


# query_char--> we are going to give the hashed version of our passwords--First 5 chars
def request_api_data(query_char):
    url = 'https://api.pwnedpasswords.com/range/' + query_char
    res = requests.get(url)
    # we need a response[`res`] here of 200 or less.Not 400.
    if res.status_code != 200:
        raise RuntimeError(
            f'Error fetching: {res.status_code}, check the api and try again')
    return res
    # --print(res)


def get_password_leaks_count(hashes, hash_to_check):
    # hashes --> the hash responses we get
    # hash_to_check--> the tail end of it that will be used by us to compare with our own tail end.

    hashes = (line.split(':') for line in hashes.text.splitlines())
    # spilting it to the hashes we get as response and to number of times hacked
    # converting it to a tuple and spliting with :
    # h-->hash//count-->number of times hacked found in response generator object

    # now, we loop through the genrator objects
    for h, count in hashes:
        # looping through all the response hashes we got.

        #--print(h, count)
        if h == hash_to_check:
            return count  # return the count if our tail end is found in the hashes
    return 0


def pwned_api_check(password):

    sha1password = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
    # converts to UpperCase like the hashes seen and stores them in hexadecimal string format

    first5_char, tail = sha1password[:5], sha1password[5:]
    # spliting or dividing values of the hash
    # first5_char is the chars needed
    # tail is the remaining tail end we will compare with `hash_to_check`

    response = request_api_data(first5_char)
    # now we will get a tonne of hashes whose first 5 chars matches our own head

    return get_password_leaks_count(response, tail)
    # to get the count of how many times our password was hacked

    # --print(sha1password)

    # --print(response)


def main(args):
    # this is the one which will accept our inputs and check them in the CL.

    for password in args:
        count = pwned_api_check(password)
        if count:
            print(
                f'{password} was found {count} times \U0001F62C... you should probably change your password!')
        else:
            print(f'{password} was NOT found. Carry on!')
            print("Leading You To The Safe Land", "\N{winking face}")
    return 'done!'



if __name__ == '__main__':  # Since this should be our main module.
    sys.exit(main(sys.argv[1:]))
    # system call exits and bring is back to command line

# done will be returned too bacuse we exit the entire process

##
# the generator objects must be splitted in order to check the hashes recieved as responses.
# these will give you the number of times the password you input was hacked or esle you can't check them.

# hashlib- Read the Documentation To Know More because even I'm confused right now
#      https://docs.python.org/3/library/hashlib.html
#      https://docs.python.org/3/library/string.html

# ________________________________________________________________________________________________________________________________
# @ NOTE
#                                                                                                                       |
# Now, different computers have different shells. There might be some apps or other things that will be running on your         |
# command line or terminal. These might record or save your passowrd. So it is practically better to use the password           |
# from another text file.                                                                                                       |
# You can do it like:                                                                                                           |
#                                                                                                                               |
#                                                                                                                               |
#                  
#                                                                                          |                                    |
# password_in_seperate_file = sys.argv[1]                 <---->                           |                                    |
#                                                           -|                             |                                    |
# if __name__ == '__main__':                                 |   <<------------------------|                                    |
#    sys.exit(main(password_in_seperate_file))               |                                                                  |
#    sys.exit(main(sys.argv[1:]))  Another way             __|                                                                  |
#                                                                                                                               |
#                                                                                                                               |
# ______________________________________________________________________________________________________________________________|

# “The world is indeed full of peril, and in it there are many dark places
# greater.” but still there is much that is fair, and though in all lands love is now mingled with grief, it grows perhaps the
# BE SAFE :)
