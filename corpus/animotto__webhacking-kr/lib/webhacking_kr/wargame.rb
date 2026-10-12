# frozen_string_literal: true

require 'uri'
require 'net/http'

module WebhackingKR
  ##
  # Wargame
  class Wargame
    BASE_URI = 'https://webhacking.kr'
    QUERY_LOGIN = '/login.php?login'
    QUERY_CHALLENGE = '/chall.php'
    QUERY_AUTH = '/auth.php'

    attr_reader :challenges
    attr_accessor :user_id, :password, :session_id, :challenge

    def initialize(shell)
      @shell = shell

      @user_id = ENV['WEBHACK_KR_USERID']
      @password = ENV['WEBHACK_KR_PASSWORD']

      uri = URI(BASE_URI)
      @client = Net::HTTP.new(uri.host, uri.port)
      @client.use_ssl = uri.instance_of?(URI::HTTPS)
      @session_id = nil

      @challenge = 1
      @challenges = []
      ChallengeBase.successors.each { |successor| @challenges << successor.new(@shell, self, @client) }
    end

    def login
      request = Net::HTTP::Post.new(QUERY_LOGIN)
      request.set_form_data(
        {
          'id' => @user_id,
          'pw' => @password
        }
      )
      begin
        response = @client.request(request)
      rescue StandardError => e
        raise HTTPError, e
      end
      return if response.body =~ /Login Failed/
      return unless response['Set-Cookie']

      response['Set-Cookie'].split('; ').each do |var|
        val = var.split('=')
        next unless val[0] == 'PHPSESSID'

        @session_id = val[1]
      end

      !@session_id.nil?
    end

    def auth(flag)
      request = Net::HTTP::Post.new(
        QUERY_AUTH,
        { 'Cookie' => "PHPSESSID=#{@session_id}" }
      )
      request.set_form_data('flag' => flag)
      begin
        response = @client.request(request)
      rescue StandardError => e
        raise HTTPError, e
      else
        response.body
      end
    end

    def status
      begin
        response = @client.get(
          QUERY_CHALLENGE,
          { 'Cookie' => "PHPSESSID=#{@session_id}" }
        )
      rescue StandardError => e
        raise HTTPError, e
      end
      match = /userid : (\S+), score : (\d+)/.match(response.body)
      return unless match

      {
        login: match[1],
        score: match[2]
      }
    end

    def exec
      challenge = @challenges.detect { |l| l.class::CHALLENGE == @challenge }
      unless challenge
        @shell.log('Unknown challenge')
        return
      end

      challenge.exec
    end
  end

  ##
  # HTTP error
  class HTTPError < StandardError
  end
end
