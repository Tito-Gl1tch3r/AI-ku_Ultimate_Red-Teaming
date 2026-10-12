require 'spec_helper'
require 'byebug'

Forminator.configure do |config|
  config.klass = :user
  config.persist = -> (user) { user.save }
  config.steps = [FirstStep]
end

RSpec.describe Forminator do
  it 'has a version number' do
    expect(Forminator::VERSION).not_to be nil
  end
end

RSpec.describe Forminator::Step do
  subject { FirstStep }
  let(:params) { { email: 'test@test.com', name: 'Test' } }
  let(:invalid_params) { { email: 'test@test.com' } }
  let(:object) do
    Object.class_eval { def save; true end }
  end

  describe '.call' do

    it 'initializes a step and validates it' do
      stub_step_persistence

      described_class.call(object, params)
    end

    it 'initializes a step and calls a custom persist logic' do
      persistence_logic = -> (object) { object.save }
      stub_step_persistence(custom_persist: persistence_logic)

      described_class.call(object, params, persist: persistence_logic)
    end

    it 'returns the validity and initial params if valid' do
      expect(subject.call(object, params)).to eq [{ valid: true }, params]
    end

    it 'returns the validity and initial params if not valid' do
      expect(subject.call(object, invalid_params)).to eq [{ valid: false }, invalid_params]
    end
  end

  describe '#valid?' do
    it 'returns true - the params are valid' do
      expect(subject.new(params).valid?).to be true
    end

    it 'returns false - the params are not valid' do
      expect(subject.new(invalid_params).valid?).to be false
    end
  end

  describe '#persist?' do
    it 'returns true - persists the object' do
      expect(subject.new(params).persist?).to be true
    end

    it 'returns false - does not persist the object' do
      subject.class_eval { def persist?; false; end; }

      expect(subject.new(params).persist?).to be false
    end
  end

  describe '#persist' do
    it 'calls the configured persistence method of the step' do
      user = instance_double('User', save: true)
      persistence_logic = Forminator.config.persist

      expect(Forminator.config).to receive(:persist) { persistence_logic }
      expect(persistence_logic).to receive(:call).with(user)

      subject.new(params).persist(object: user)
    end

    it 'calls a custom persistence mechanism for each step' do
      user = instance_double('User', save: true)
      persistence_logic = -> (user) { user.save }

      expect(persistence_logic).to receive(:call).with(user)
      expect(user).to receive(:save)

      subject.new(params).persist(object: user, persist: persistence_logic)
    end
  end

  private

  def stub_step_persistence(custom_persist: nil)
    step = instance_double(Forminator::Step, valid?: true, persist?: true)
    expect(described_class).to receive(:new).with(params) { step }
    expect(step).to receive(:valid?)
    expect(step).to receive(:persist).with(object: object, persist: custom_persist)
  end
end
