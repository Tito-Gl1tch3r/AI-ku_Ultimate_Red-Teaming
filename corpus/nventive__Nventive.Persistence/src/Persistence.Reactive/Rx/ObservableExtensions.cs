using System;
using System.Reactive;
using System.Reactive.Concurrency;
using System.Reactive.Linq;
using System.Reactive.Disposables;
using System.Threading;
using System.Threading.Tasks;
using Uno;

namespace Nventive.Persistence
{
	/// <summary>
	/// Provides a set of static methods for writing in-memory queries over observable sequences.
	/// </summary>
	internal static partial class ObservableExtensions
	{
		/// <summary>
		/// Converts to asynchronous function into an observable sequence. Each subscription to the resulting sequence causes the function to be started.
		/// The CancellationToken passed to the asynchronous function is tied to the observable sequence's subscription that triggered the function's invocation and can be used for best-effort cancellation.
		/// </summary>
		/// <remarks>
		/// This operator is the same as <see cref="Observable.FromAsync{TResult}(System.Func{System.Threading.Tasks.Task{TResult}})"/> except that it 
		/// ensure to run synchronously the completion instead of running it on an uncontrolled context (i.e. TaskPool).
		/// </remarks>
		/// <typeparam name="T">The type of the result returned by the asynchronous function.</typeparam>
		/// <param name="factory">Asynchronous function to convert.</param>
		/// <returns>An observable sequence exposing the result of invoking the function, or an exception.</returns>
		/// <exception cref="ArgumentNullException"><paramref name="factory"/> is null.</exception>
		/// <remarks>When a subscription to the resulting sequence is disposed, the CancellationToken that was fed to the asynchronous function will be signaled.</remarks>
		internal static IObservable<T> FromAsync<T>(FuncAsync<T> factory, IScheduler scheduler = null)
		{
			// The issue with Observable.FromAsync() is that the observer.OnNext() which will complete the task is 
			// executed in a ContinueWith, i.e. using an unknown SynchronizationContext (Default TaskPool), so all 
			// subscribers will receive and handle the value with an invalid context.

			var o = Observable.Create<T>(async (observer, ct) =>
			{
				try
				{
					var result = await factory(ct);
					observer.OnNext(result);
					observer.OnCompleted();
				}
				catch (Exception e)
				{
					observer.OnError(e);
				}
			});

			o = scheduler != null ? o.SubscribeOn(scheduler) : o;

			return o;
		}

		/// <summary>
		/// This is a special SelectMany who ensure to immediately dispose the previous SelectMany result on a new value.
		/// </summary>
		internal static IObservable<TResult> SelectManyDisposePrevious<TSource, TResult>(this IObservable<TSource> source, Func<TSource, IObservable<TResult>> selector)
		{
			return Observable.Create<TResult>(
				observer =>
				{
					var serialDisposable = new SerialDisposable();
					var gate = new object();
					var isWorking = false; // We are currently observing a child
					var isCompleted = false; // The parent observable has completed

					var disposable = source.Subscribe(
						next =>
						{
							isWorking = true;
							serialDisposable.Disposable = null;
							var projectedSource = selector(next);
							serialDisposable.Disposable = projectedSource
								.Subscribe(
									observer.OnNext,
									observer.OnError,
									() =>
									{
										lock (gate)
										{
											isWorking = false;
											if (isCompleted)
											{
												observer.OnCompleted();
											}
										}
									}
								);
						},
						observer.OnError,
						() =>
						{
							lock (gate)
							{
								isCompleted = true;
								if (!isWorking)
								{
									observer.OnCompleted();
								}
							}
						});

					return new CompositeDisposable(disposable, serialDisposable).Dispose;
				});
		}

		/// <summary>
		/// A SelectMany who ensure to immediately dispose the previous SelectMany result on a new value.
		/// </summary>
		internal static IObservable<TResult> SelectManyDisposePrevious<TSource, TResult>(
			this IObservable<TSource> source,
			Func<TSource, CancellationToken, Task<TResult>> selector,
			IScheduler scheduler = null)
		{
			return SelectManyDisposePrevious(
				source,
				v => ObservableExtensions.FromAsync(ct => selector(v, ct), scheduler)
			);
		}

		/// <summary>
		/// Provide an async staring value which is propagated only until the source produce its first value, then continue with the source sequence.
		/// </summary>
		/// <typeparam name="T">Type of the values in the observable sequence</typeparam>
		/// <param name="source">The source observable sequence.</param>
		/// <param name="valueProvider">Provider of the value to prepend to the source.</param>
		/// <returns>An observable sequence with the provided value at the beginning if no value produced by the source.</returns>
		internal static IObservable<T> TryStartWith<T>(this IObservable<T> source, FuncAsync<T> valueProvider)
			=> source.TryStartWith(Observable.Defer(() => Observable.StartAsync(ct => valueProvider(ct))));

		/// <summary>
		/// Provide a staring observable sequence from which values are propagated only until the source produce its first value, then continue with the source sequence.
		/// </summary>
		/// <typeparam name="T">Type of the values in the observable sequence</typeparam>
		/// <param name="source">The source observable sequence.</param>
		/// <param name="initialValues">The observable sequence to use until the source produces its values.</param>
		/// <returns>An observable sequence with the provided value at the beginning if no value produced by the source.</returns>
		internal static IObservable<T> TryStartWith<T>(this IObservable<T> source, IObservable<T> initialValues)
		{
			return Observable.Create<T>(observer =>
			{
				// The gate is required to ensure that both subscriptions will
				// not race each others into observer.OnNext().
				// This may happen if initialValues.OnNext is called while source.OnNext is disposing
				// the subscription to initialValues.
				//
				// The Synchronize operator prevents observer.OnNext to be concurrently called.

				var gate = new object();


				var initialSubscription = new SingleAssignmentDisposable();
				var subscription = source
					.Synchronize(gate)
					.Subscribe(
						v => {
							initialSubscription.Dispose();
							observer.OnNext(v);
						},
						e => {
							initialSubscription.Dispose();
							observer.OnError(e);
						},
						() => {
							initialSubscription.Dispose();
							observer.OnCompleted();
						}
					);

				initialSubscription.Disposable = initialValues
					.Synchronize(gate)
					.Subscribe(
						v => {
							if (!initialSubscription.IsDisposed)
							{
								observer.OnNext(v);
							}
						},
						e => {
							if (!initialSubscription.IsDisposed)
							{
								observer.OnError(e);
							}
						});

				return new CompositeDisposable(initialSubscription, subscription);
			});
		}
	}
}
