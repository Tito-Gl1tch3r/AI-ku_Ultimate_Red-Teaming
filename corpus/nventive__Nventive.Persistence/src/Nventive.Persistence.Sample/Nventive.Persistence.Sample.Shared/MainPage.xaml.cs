using Microsoft.UI.Xaml.Controls;
using System.Text.Json;
using System.Reactive.Concurrency;
using Microsoft.UI.Xaml;
using System.Threading;
using System;
using System.Text.Json.Serialization;

// The Blank Page item template is documented at http://go.microsoft.com/fwlink/?LinkId=402352&clcid=0x409

namespace Nventive.Persistence.Sample
{
	/// <summary>
	/// An empty page that can be used on its own or navigated to within a Frame.
	/// </summary>
	public sealed partial class MainPage : Page
	{
		private readonly IObservableDataPersister<string> _dataPersister;

		public MainPage()
		{
			this.InitializeComponent();
			_dataPersister = CreateSecureDataPersister(defaultValue: string.Empty);
		}

		private async void SaveButtonClicked(object sender, RoutedEventArgs e)
		{
			await _dataPersister.Update(CancellationToken.None, context =>
			{
				var value = context.GetReadValueOrDefault(string.Empty);
				context.Commit(this.ValueToSaveTextBox.Text);
			});
		}

		private async void ReadButtonClicked(object sender, RoutedEventArgs e)
		{
			var result = await _dataPersister.Load(CancellationToken.None);

			DispatcherQueue.TryEnqueue(() =>
			{
				this.ReadValueTextBlock.Text = result.Value ?? string.Empty;
			});
		}

		private IObservableDataPersister<T> CreateSecureDataPersister<T>(T defaultValue = default(T))
		{
#if __ANDROID__
			return new SettingsStorageObservableDataPersisterAdapter<T>(
				storage: new KeyStoreSettingsStorage(
					new JsonSerializerToSettingsSerializerAdapter(
						new JsonSerializerOptions
						{
							AllowTrailingCommas = true,
							NumberHandling = JsonNumberHandling.AllowReadingFromString,
							PropertyNameCaseInsensitive = true,
						}
					),
					Uno.UI.ContextHelper.Current.GetFileStreamPath(typeof(T).Name).AbsolutePath
				),
				key: typeof(T).Name,
				comparer: null,
				concurrencyProtection: false
			);
#elif __IOS__
			return new SettingsStorageObservableDataPersisterAdapter<T>(
				storage: new KeychainSettingsStorage(
					new JsonSerializerToSettingsSerializerAdapter(
						new JsonSerializerOptions
						{
							AllowTrailingCommas = true,
							NumberHandling = JsonNumberHandling.AllowReadingFromString,
							PropertyNameCaseInsensitive = true,
						}
					)
				),
				key: typeof(T).Name,
				comparer: null,
				concurrencyProtection: false
			);
#else
			return CreateDataPersister(defaultValue);
#endif
		}

		private IObservableDataPersister<T> CreateDataPersister<T>(T defaultValue = default)
		{
			return UnoDataPersister.CreateFromFile<T>(
				FolderType.WorkingData,
				typeof(T).Name + ".json",
				async (ct, s) => await JsonSerializer.DeserializeAsync<T>(s, cancellationToken: ct),
				async (ct, v, s) => await JsonSerializer.SerializeAsync<T>(s, v, cancellationToken: ct)
			)
			.ToObservablePersister(TaskPoolScheduler.Default.ToBackgroundScheduler());
		}
	}

	public sealed class JsonSerializerToSettingsSerializerAdapter : ISettingsSerializer
	{
		private JsonSerializerOptions _options;

		public JsonSerializerToSettingsSerializerAdapter(JsonSerializerOptions options)
		{
			_options = options;
		}

		public object FromString(string source, Type targetType)
		{
			return JsonSerializer.Deserialize(source, targetType, _options);
		}

		public string ToString(object value, Type valueType)
		{
			return JsonSerializer.Serialize(value, valueType, _options);
		}
	}
}
