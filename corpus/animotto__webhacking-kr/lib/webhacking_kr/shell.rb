# frozen_string_literal: true

require 'readline'
require 'io/console'

module WebhackingKR
  ##
  # Shell
  class Shell
    PROMPT = 'webhacking.kr> '
    BANNER = <<~ENDBANNER
      _______________________

       webhacking.kr wargame
      _______________________

    ENDBANNER

    COMMANDS = {
      'login' => ['l', '<user_id> [password]', 'Login'],
      'status' => ['s', '', 'Show your status'],
      'challenge' => ['c', '[n]', 'Run challenge'],
      'help' => ['?', '', 'This help'],
      'quit' => ['q', '', 'Quit']
    }.freeze

    def initialize
      @input = $stdin
      @output = $stdout
      @running = false
      @wargame = Wargame.new(self)
      Readline.completion_proc = proc { |s| COMMANDS.keys.grep(/^#{s}/) }
    end

    def log(message)
      @output.puts(message)
    end

    def read_password(prompt = 'Password: ')
      @output.print(prompt)
      line = @input.noecho(&:gets).chomp
      @output.puts
      line
    end

    def run
      log(BANNER)
      @running = true
      loop do
        break unless @running

        line = Readline.readline(PROMPT, true)
        unless line
          @running = false
          next
        end

        line.strip!
        if line.empty?
          Readline::HISTORY.pop
          next
        end

        words = line.split(/\s+/)
        cmd = words[0].downcase
        case cmd
        when 'q', 'quit'
          @running = false

        when 'l', 'login'
          if words.length < 2 && @wargame.user_id.nil?
            log('Specify user id and password')
            next
          end

          @wargame.user_id = words[1] if words.length >= 2

          if words.length >= 3
            @wargame.password = words[2]
          elsif @wargame.password.nil?
            @wargame.password = read_password
          end

          unless @wargame.login
            log('Login failed!')
            next
          end

          log('Logged in')

        when 's', 'status'
          unless @wargame.session_id
            log('Not logged in')
            next
          end

          status = @wargame.status
          unless status
            log('Failed!')
            next
          end

          log('Status:')
          status.each do |k, v|
            log(
              format(
                ' %<key>-15s%<value>s',
                key: k.capitalize,
                value: v
              )
            )
          end

        when 'c', 'challenge'
          if words.length < 2
            log('Available challenges:')
            @wargame.challenges.each.with_index do |challenge, i|
              if (i % 10).zero?
                @output.puts unless i.zero?
                @output.print(' ')
              end
              @output.print(format('%2d ', challenge.class::CHALLENGE))
            end
            @output.puts
            next
          end

          unless @wargame.session_id
            log('Not logged in')
            next
          end

          @wargame.challenge = words[1].to_i
          @wargame.exec

        when '?', 'help'
          log('Commands:')
          COMMANDS.each do |k, v|
            log(
              format(
                ' %<short>s %<long>-30s%<desc>s',
                short: v[0],
                long: "#{k} #{v[1]}",
                desc: v[2]
              )
            )
          end

        else
          log('Unknown command')
        end
      rescue Interrupt
        next
      rescue HTTPError => e
        log("HTTP error: #{e}")
      end
    end
  end
end
