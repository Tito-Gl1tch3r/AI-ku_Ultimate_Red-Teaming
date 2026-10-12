using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Styling;
using Avalonia.Threading;
using SubdomainScanner.Avalonia.ViewModels;
using System.Collections.Specialized;
using System.ComponentModel;

namespace SubdomainScanner.Avalonia.Views;

public partial class MainWindow : Window
{
    private ScrollViewer? _logsScrollViewer;

    public MainWindow()
    {
        InitializeComponent();

        // Subscribe to DataContext changes
        DataContextChanged += OnDataContextChanged;
    }

    private void DomainTextBox_KeyDown(object? sender, KeyEventArgs e)
    {
        // Trigger scan when Enter key is pressed
        if (e.Key == Key.Enter && DataContext is MainWindowViewModel viewModel)
        {
            if (viewModel.StartScanCommand.CanExecute(null))
            {
                viewModel.StartScanCommand.Execute(null);
            }
            e.Handled = true;
        }
    }

    private void OnDataContextChanged(object? sender, System.EventArgs e)
    {
        if (DataContext is MainWindowViewModel viewModel)
        {
            // Set initial theme
            UpdateTheme(viewModel.IsDarkMode);

            // Subscribe to IsDarkMode property changes
            viewModel.PropertyChanged += OnViewModelPropertyChanged;

            // Subscribe to Logs collection changes for auto-scroll
            viewModel.Logs.CollectionChanged += OnLogsCollectionChanged;

            // Find the ScrollViewer for logs
            _logsScrollViewer = this.FindControl<ScrollViewer>("LogsScrollViewer");
        }
    }

    private void OnViewModelPropertyChanged(object? sender, PropertyChangedEventArgs e)
    {
        if (e.PropertyName == nameof(MainWindowViewModel.IsDarkMode) && sender is MainWindowViewModel viewModel)
        {
            UpdateTheme(viewModel.IsDarkMode);
        }
    }

    private void OnLogsCollectionChanged(object? sender, NotifyCollectionChangedEventArgs e)
    {
        // Auto-scroll to bottom when new logs are added
        if (e.Action == NotifyCollectionChangedAction.Add && _logsScrollViewer != null)
        {
            Dispatcher.UIThread.Post(() =>
            {
                _logsScrollViewer.ScrollToEnd();
            }, DispatcherPriority.Background);
        }
    }

    private void UpdateTheme(bool isDarkMode)
    {
        RequestedThemeVariant = isDarkMode ? ThemeVariant.Dark : ThemeVariant.Light;
    }
}