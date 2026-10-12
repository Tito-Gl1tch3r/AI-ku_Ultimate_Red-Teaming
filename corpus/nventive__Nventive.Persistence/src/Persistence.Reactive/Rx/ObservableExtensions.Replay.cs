using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Reactive.Linq;
using System.Reactive.Concurrency;
using System.Reactive.Disposables;
using System.Reactive.Subjects;
using Uno.Collections;
using Uno.Extensions;
using System.Threading;

namespace Nventive.Persistence
{
	internal static partial class ObservableExtensions
	{
		internal static IObservable<T> ReplayOneRefCount<T>(this IObservable<T> source, IScheduler scheduler)
		{
			var factory =
				new MultipleRefCountDisposableFactory<ReplayOneRefCountInnerSubscription<T>>(
					() => new ReplayOneRefCountInnerSubscription<T>(source, scheduler));

			return Observable.Create<T>(
				observer =>
				{
					var refcountedSubscription = factory.CreateDisposable();

					var localSubscription =
						refcountedSubscription.Instance.ReplayOneSubject.Subscribe(observer);

					return new CompositeDisposable
						{
							localSubscription,
							refcountedSubscription
						};
				});
		}

		internal class ReplayOneRefCountInnerSubscription<T> : IDisposable
		{
			private readonly CompositeDisposable _disposables;

			internal ReplayOneSubject<T> ReplayOneSubject { get; }

			internal ReplayOneRefCountInnerSubscription(IObservable<T> source, IScheduler scheduler)
			{
				ReplayOneSubject = new ReplayOneSubject<T>(scheduler);

				_disposables =
					new CompositeDisposable
					{
						source.Subscribe(ReplayOneSubject),
						ReplayOneSubject
					};
			}

			public void Dispose()
			{
				_disposables.Dispose();
			}
		}

		/// <summary>
		/// This class is a building block for services who needs to share a unique disposable
		/// for which the lifetime is handle by the number of active subscriptions.
		/// </summary>
		/// <remarks>
		/// Don't forgive to dispose all subscriptions!
		/// </remarks>
		internal class MultipleRefCountDisposableFactory<T> : IDisposable where T : class, IDisposable
		{
			private readonly Func<T> _factory;
			private T _current;
			private int _refcount;

			private object _lock = new object();

			public MultipleRefCountDisposableFactory(Func<T> factory)
			{
				_factory = factory;
			}

			/// <summary>
			/// Create a new instance subscription of the inner service
			/// </summary>
			/// <remarks>
			/// On first disposable created, the inner factory is invoked.
			/// When all generated disposables are disposed, the inner service is
			/// disposed.
			/// If new disposables are created again, the inner service is created again.
			/// 
			/// WARNING: You can have a reference to the inner service from the subscription.
			/// Don't dispose it manually or you'll have a disposed shared service!  Let this
			/// component dispose it for you at the right time.
			/// </remarks>
			public MultipleRefCountDisposableSubscription CreateDisposable()
			{
				lock (_lock)
				{
					var newCount = Interlocked.Increment(ref _refcount);
					if (newCount < 1)
					{
						throw new ObjectDisposedException(GetType().Name);
					}

					if (newCount == 1)
					{
						_current = _factory();
					}

					return new MultipleRefCountDisposableSubscription(Decrease, _current);
				}
			}

			private void Decrease()
			{
				lock (_lock)
				{
					var newCount = Interlocked.Decrement(ref _refcount);

					if (newCount > 0)
					{
						return; // no clean-up to do (ref remainings)
					}

					if (_current == null)
					{
						return; // already cleaned-up ?  We're probably disposing the service
					}

					_current.Dispose(); // dispose managed object
					_current = null;
				}
			}

			public void Dispose()
			{
				Interlocked.Exchange(ref _refcount, -1);
				Decrease();
			}

			public sealed class MultipleRefCountDisposableSubscription : IDisposable
			{
				public T Instance { get; private set; }

				private Action _onDispose;

				internal MultipleRefCountDisposableSubscription(Action onDispose, T instance)
				{
					Instance = instance;
					_onDispose = onDispose;
				}

				public void Dispose()
				{
					var disposeAction = Interlocked.Exchange(ref _onDispose, null);
					if (disposeAction == null)
					{
						throw new ObjectDisposedException(GetType().Name);
					}
					disposeAction();
				}
			}
		}
	}
}
