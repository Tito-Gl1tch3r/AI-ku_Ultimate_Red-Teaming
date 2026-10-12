using System;
using System.Collections.Concurrent;
using System.Reactive;
using System.Reactive.Concurrency;
using System.Reactive.Disposables;
using System.Reactive.Subjects;
using System.Threading.Tasks;
using Uno.Collections;
using Uno.Threading;

namespace Nventive.Persistence
{
	[Flags]
	internal enum ReplayOneSubjectMode
	{
		Default,
		FlushValueOnError,
		FlushValueOnCompleted,
	}

	/// <summary>
	/// A replay subject optimized to provide a single value
	/// </summary>
	/// <typeparam name="T"></typeparam>
	internal sealed class ReplayOneSubject<T> : ReplayOneSubject, ISubject<T>
	{
		/// <summary>
		/// Initializes specialized version of <see cref="System.Reactive.Subjects.ReplaySubject&lt;T&gt;" /> with a fixed one item buffer.
		/// </summary>
		/// <param name="scheduler">Scheduler the observers are invoked on.</param>
		/// <exception cref="ArgumentNullException"><paramref name="scheduler"/> is null.</exception>
		public ReplayOneSubject(IScheduler scheduler, ReplayOneSubjectMode mode = ReplayOneSubjectMode.Default) : base(scheduler, mode)
		{
		}

		/// <summary>
		/// Initializes with an initial value a specialized version of <see cref="System.Reactive.Subjects.ReplaySubject&lt;T&gt;" /> with a fixed one item buffer.
		/// </summary>
		/// <param name="scheduler">Scheduler the observers are invoked on.</param>
		/// <param name="initialValue">The initial value of the subject (equivalent to call subject.<see cref="OnNext"/>(initialValue); )</param>
		/// <exception cref="ArgumentNullException"><paramref name="scheduler"/> is null.</exception>
		public ReplayOneSubject(IScheduler scheduler, T initialValue, ReplayOneSubjectMode mode = ReplayOneSubjectMode.Default) : base(scheduler, initialValue, mode)
		{
		}

		public void OnNext(T value) => base.OnNext((object)value);

		public IDisposable Subscribe(IObserver<T> observer) => base.Subscribe(new GenericToObjectObserverAdapter<T>(observer));
	}

	internal class GenericToObjectObserverAdapter<T> : IObserver<object>
	{
		private readonly IObserver<T> _source;

		public GenericToObjectObserverAdapter(IObserver<T> source)
		{
			if (source == null)
			{
				throw new ArgumentNullException(nameof(source));
			}

			_source = source;
		}

		public void OnNext(object value) => _source.OnNext((T)value);

		public void OnNext(T value) => _source.OnNext(value);

		public void OnCompleted() => _source.OnCompleted();

		public void OnError(Exception error) => _source.OnError(error);
	}

	internal class ReplayOneSubject : ISubject<object>, IDisposable
	{
		private readonly IScheduler _scheduler;
		private readonly bool _flushValueOnError;
		private readonly bool _flushValueOnCompleted;

		private object _value;
		private bool _hasValue = false;
		private bool _isStopped;
		private Exception _error;

		private ImmutableList<ScheduledObserver> _observers;
		private bool _isDisposed;

		private readonly object _gate = new object();

		/// <summary>
		/// Initializes specialized version of <see cref="System.Reactive.Subjects.ReplaySubject&lt;T&gt;" /> with a fixed one item buffer.
		/// </summary>
		/// <param name="scheduler">Scheduler the observers are invoked on.</param>
		/// <exception cref="ArgumentNullException"><paramref name="scheduler"/> is null.</exception>
		internal ReplayOneSubject(IScheduler scheduler, ReplayOneSubjectMode mode = ReplayOneSubjectMode.Default)
		{
			if (scheduler == null)
				throw new ArgumentNullException("scheduler");

			_scheduler = scheduler;
			_flushValueOnError = (mode & ReplayOneSubjectMode.FlushValueOnError) == ReplayOneSubjectMode.FlushValueOnError;
			_flushValueOnCompleted = (mode & ReplayOneSubjectMode.FlushValueOnCompleted) == ReplayOneSubjectMode.FlushValueOnCompleted;

			_isStopped = false;
			_error = null;

			_observers = new ImmutableList<ScheduledObserver>();
		}

		/// <summary>
		/// Initializes with an initial value a specialized version of <see cref="System.Reactive.Subjects.ReplaySubject&lt;T&gt;" /> with a fixed one item buffer.
		/// </summary>
		/// <param name="scheduler">Scheduler the observers are invoked on.</param>
		/// <param name="initialValue">The initial value of the subject (equivalent to call subject.<see cref="OnNext"/>(initialValue); )</param>
		/// <exception cref="ArgumentNullException"><paramref name="scheduler"/> is null.</exception>
		internal ReplayOneSubject(IScheduler scheduler, object initialValue, ReplayOneSubjectMode mode = ReplayOneSubjectMode.Default)
			: this(scheduler, mode)
		{
			OnNext(initialValue);
		}

		/// <summary>
		/// Indicates whether the subject has observers subscribed to it.
		/// </summary>
		public bool HasObservers
		{
			get
			{
				var observers = _observers;
				return observers != null && observers.Data.Length > 0;
			}
		}

		/// <summary>
		/// Notifies all subscribed and future observers about the arrival of the specified element in the sequence.
		/// </summary>
		/// <param name="value">The value to send to all observers.</param>
		public void OnNext(object value)
		{
			var o = default(ScheduledObserver[]);

			lock (_gate)
			{
				CheckDisposed();

				if (!_isStopped)
				{
					_value = value;
					_hasValue = true;

					o = _observers.Data;
					foreach (var observer in o)
						observer.OnNext(_value);
				}
			}

			if (o != null)
			{
				foreach (var observer in o)
				{
					observer.EnsureActive();
				}
			}
		}

		/// <summary>
		/// Notifies all subscribed and future observers about the specified exception.
		/// </summary>
		/// <param name="error">The exception to send to all observers.</param>
		/// <exception cref="ArgumentNullException"><paramref name="error"/> is null.</exception>
		public void OnError(Exception error)
		{
			if (error == null)
				throw new ArgumentNullException("error");

			var o = default(ScheduledObserver[]);
			lock (_gate)
			{
				CheckDisposed();

				if (!_isStopped)
				{
					_isStopped = true;
					_error = error;

					if (_flushValueOnError)
					{
						_value = default(object);
						_hasValue = false;
					}

					o = _observers.Data;
					foreach (var observer in o)
						observer.OnError(error);

					_observers = new ImmutableList<ScheduledObserver>();
				}
			}

			if (o != null)
			{
				foreach (var observer in o)
				{
					observer.EnsureActive();
				}
			}
		}

		/// <summary>
		/// Notifies all subscribed and future observers about the end of the sequence.
		/// </summary>
		public void OnCompleted()
		{
			var o = default(ScheduledObserver[]);
			lock (_gate)
			{
				CheckDisposed();

				if (!_isStopped)
				{
					_isStopped = true;

					if (_flushValueOnCompleted)
					{
						_value = default(object);
						_hasValue = false;
					}

					o = _observers.Data;
					foreach (var observer in o)
						observer.OnCompleted();

					_observers = new ImmutableList<ScheduledObserver>();
				}
			}

			if (o != null)
				foreach (var observer in o)
					observer.EnsureActive();
		}

		/// <summary>
		/// Subscribes an observer to the subject.
		/// </summary>
		/// <param name="observer">Observer to subscribe to the subject.</param>
		/// <returns>Disposable object that can be used to unsubscribe the observer from the subject.</returns>
		/// <exception cref="ArgumentNullException"><paramref name="observer"/> is null.</exception>
		public virtual IDisposable Subscribe(IObserver<object> observer)
		{
			if (observer == null)
				throw new ArgumentNullException("observer");

			var so = new ScheduledObserver(_scheduler, observer);

			var n = 0;

			var subscription = new RemovableDisposable(this, so);
			lock (_gate)
			{
				CheckDisposed();

				//
				// Notice the v1.x behavior of always calling Trim is preserved here.
				//
				// This may be subject (pun intended) of debate: should this policy
				// only be applied while the sequence is active? With the current
				// behavior, a sequence will "die out" after it has terminated by
				// continuing to drop OnNext notifications from the queue.
				//
				// In v1.x, this behavior was due to trimming based on the clock value
				// returned by scheduler.Now, applied to all but the terminal message
				// in the queue. Using the IStopwatch has the same effect. Either way,
				// we guarantee the final notification will be observed, but there's
				// no way to retain the buffer directly. One approach is to use the
				// time-based TakeLast operator and apply an unbounded ReplaySubject
				// to it.
				//
				// To conclude, we're keeping the behavior as-is for compatibility
				// reasons with v1.x.
				//
				_observers = _observers.Add(so);

				if (_hasValue)
				{
					n++;
					so.OnNext(_value);
				}

				if (_error != null)
				{
					n++;
					so.OnError(_error);
				}
				else if (_isStopped)
				{
					n++;
					so.OnCompleted();
				}
			}

			so.EnsureActive(n);

			return subscription;
		}

		void Unsubscribe(ScheduledObserver observer)
		{
			lock (_gate)
			{
				if (!_isDisposed)
					_observers = _observers.Remove(observer);
			}
		}

		sealed class RemovableDisposable : IDisposable
		{
			private readonly ReplayOneSubject _subject;
			private readonly ScheduledObserver _observer;

			public RemovableDisposable(ReplayOneSubject subject, ScheduledObserver observer)
			{
				_subject = subject;
				_observer = observer;
			}

			public void Dispose()
			{
				_observer.Dispose();
				_subject.Unsubscribe(_observer);
			}
		}

		void CheckDisposed()
		{
			if (_isDisposed)
				throw new ObjectDisposedException(string.Empty);
		}

		/// <summary>
		/// Releases all resources used by the current instance of the <see cref="System.Reactive.Subjects.ReplaySubject&lt;T&gt;"/> class and unsubscribe all observers.
		/// </summary>
		public void Dispose()
		{
			lock (_gate)
			{
				_isDisposed = true;
				_observers = null;
			}
		}
	}

	internal class ScheduledObserver : ObserverBase<object>, IDisposable
	{
		private const int STOPPED = 0;
		private const int RUNNING = 1;
		private const int PENDING = 2;
		private const int FAULTED = 9;

		private readonly ConcurrentQueue<object> _queue = new ConcurrentQueue<object>();

		private volatile bool _failed;
		private volatile Exception _error;
		private volatile bool _completed;

		private readonly IObserver<object> _observer;
		private readonly IScheduler _scheduler;
		private readonly SerialDisposable _disposable = new SerialDisposable();

		public ScheduledObserver(IScheduler scheduler, IObserver<object> observer)
		{
			_scheduler = scheduler;
			_observer = observer;
		}

		private readonly object _dispatcherInitGate = new object();
		private AsyncEvent _dispatcherEvent = new AsyncEvent(0);
		private IDisposable _dispatcherJob;

		private void EnsureDispatcher()
		{
			if (_dispatcherJob == null)
			{
				lock (_dispatcherInitGate)
				{
					if (_dispatcherJob == null)
					{
						var cancellation = new CancellationDisposable();
						_scheduler.Schedule(async () =>
						{
							await Dispatch(cancellation);
						});

						_dispatcherJob = cancellation;

						_disposable.Disposable = new CompositeDisposable(2)
							{
								_dispatcherJob,
								Disposable.Create(() => _dispatcherEvent.Release())
							};
					}
				}
			}
		}

		private async Task Dispatch(CancellationDisposable cancel)
		{
			while (true)
			{
				if (!await _dispatcherEvent.Wait(cancel.Token))
				{
					break;
				}

				if (cancel.IsDisposed)
					return;

				var next = default(object);
				while (DequeueMessage(out next))
				{
					try
					{
						_observer.OnNext(next);
					}
					catch
					{
#pragma warning disable 168
						object nop;
						while (DequeueMessage(out next))
							;
#pragma warning restore 168

						throw;
					}

					if (!await _dispatcherEvent.Wait(cancel.Token))
					{
						break;
					}

					if (cancel.IsDisposed)
						return;
				}

				if (_failed)
				{
					_observer.OnError(_error);
					Dispose();
					return;
				}

				if (_completed)
				{
					_observer.OnCompleted();
					Dispose();
					return;
				}
			}
		}

		private bool DequeueMessage(out object next)
		{
			return _queue.TryDequeue(out next);
		}

		public void EnsureActive()
		{
			EnsureActive(1);
		}

		public void EnsureActive(int n)
		{
			if (n > 0)
			{
				_dispatcherEvent.Release(n);
			}

			EnsureDispatcher();
		}

		protected override void OnNextCore(object value)
		{
			_queue.Enqueue(value);
		}

		protected override void OnErrorCore(Exception exception)
		{
			_error = exception;
			_failed = true;
		}

		protected override void OnCompletedCore()
		{
			_completed = true;
		}

		protected override void Dispose(bool disposing)
		{
			base.Dispose(disposing);

			if (disposing)
			{
				_disposable.Dispose();
			}
		}
	}
}
