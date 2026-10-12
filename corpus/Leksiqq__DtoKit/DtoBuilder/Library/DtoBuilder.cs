using Microsoft.Extensions.DependencyInjection;
using System.Reflection;
using System.Text;

namespace Net.Leksi.Dto;

/// <summary>
/// <para xml:lang="ru">
/// Класс для построения дерева объекта, ограниченного деревом применённого интерфейса
/// </para>
/// <para xml:lang="en">
/// Class for building a tree of an object, limited by the tree of the applied interface
/// </para>
/// </summary>
public class DtoBuilder
{
    /// <summary>
    /// <para xml:lang="ru">
    /// Событие для работы с хэндлером
    /// </para>
    /// <para xml:lang="en">
    /// Event for working with the handler
    /// </para>
    /// </summary>
    public event ValueRequestEventHandler? ValueRequest;

    private const string SetUp = nameof(SetUp);
    private const string ShutDown = nameof(ShutDown);
    private const string Before = nameof(Before);
    private const string After = nameof(After);
    private const string Slash = "/";
    private const string Under = "_";

    private readonly TypesForest _typesForest;
    private readonly ObjectCache _objectCache;
    private readonly Dictionary<Type, object> _probeObjects = new();
    private readonly Dictionary<Type, Dictionary<string, MethodInfo>> _helperMethods = new();
    private readonly Dictionary<object, ValueRequestEventHandler> _helperHandlers = new();

    /// <summary>
    /// <para xml:lang="ru">
    /// Целевой объект для загрузки, если он не присвоен, то создаётся новый
    /// </para>
    /// <para xml:lang="en">
    /// Target object for loading, if it is not assigned, then a new one is created
    /// </para>
    /// </summary>
    public object? Target { get; set; } = null;

    /// <summary>
    /// <para xml:lang="ru">
    /// Инициализирует "лесом" <see cref="TypesForest"/>
    /// </para>
    /// <para xml:lang="en">
    /// Initializes with "forest" <see cref="TypesForest"/>
    /// </para>
    /// </summary>
    /// <param name="typesForest"></param>
    /// <exception cref="ArgumentNullException">
    /// <para xml:lang="ru">
    /// Без "леса" ничего не построить
    /// </para>
    /// <para xml:lang="en">
    /// Nothing can be built without a "forest"
    /// </para>
    /// </exception>
    public DtoBuilder(TypesForest typesForest)
    {
        _typesForest = typesForest ?? throw new ArgumentNullException(nameof(typesForest));
        _objectCache = typesForest.ServiceProvider.GetService<ObjectCache>() ?? new ObjectCache(_typesForest);
    }

    /// <summary>
    /// <para xml:lang="ru">
    /// Строит объект с помощью объекта-хэлпера любого класса, в котором есть методы, имеющие сигнатуры специальных делегатов:
    /// <see cref="BeforeOrAfterProcessor"/>, <see cref="ValueSetter"/>
    /// и помечены специальными атрибутами:
    /// <see cref="SetupAttribute"/>, <see cref="BeforeAttribute"/>, <see cref="PathAttribute"/>, <see cref="AfterAttribute"/>, 
    /// <see cref="ShutdownAttribute"/>
    /// </para>
    /// <para xml:lang="en">
    /// Constructs an object using a helper object of any class that has methods that have special delegate signatures:
    /// <see cref="BeforeOrAfterProcessor"/>, <see cref="ValueSetter"/>
    /// and are marked with special attributes:
    /// <see cref="SetupAttribute"/>, <see cref="BeforeAttribute"/>, <see cref="PathAttribute"/>, <see cref="AfterAttribute"/>,
    /// <see cref="ShutdownAttribute"/>
    /// </para>
    /// </summary>
    /// <typeparam name="T">
    /// <para xml:lang="ru">
    /// Интерфейс, применяемый для строительства
    /// </para>
    /// <para xml:lang="en">
    /// Interface used for construction
    /// </para>
    /// </typeparam>
    /// <param name="helper"></param>
    /// <returns>
    /// <para xml:lang="ru">
    /// Готовый объект
    /// </para>
    /// <para xml:lang="en">
    /// Ready object
    /// </para>
    /// </returns>
    /// <exception cref="ArgumentNullException">
    /// <para xml:lang="ru">
    /// Без хэлпера не работает
    /// </para>
    /// <para xml:lang="en">
    /// Doesn't work without a helper
    /// </para>
    /// </exception>
    public T? Build<T>(object helper) where T : class
    {
        return (T?)BuildOfType(typeof(T), helper);
    }

    /// <summary>
    /// <para xml:lang="ru">
    /// Строит объект с помощью объекта-хэлпера любого класса, в котором есть методы, имеющие сигнатуры специальных делегатов:
    /// <see cref="BeforeOrAfterProcessor"/>, <see cref="ValueSetter"/>
    /// и помечены специальными атрибутами:
    /// <see cref="SetupAttribute"/>, <see cref="BeforeAttribute"/>, <see cref="PathAttribute"/>, <see cref="AfterAttribute"/>, 
    /// <see cref="ShutdownAttribute"/>
    /// </para>
    /// <para xml:lang="en">
    /// Constructs an object using a helper object of any class that has methods that have special delegate signatures:
    /// <see cref="BeforeOrAfterProcessor"/>, <see cref="ValueSetter"/>
    /// and are marked with special attributes:
    /// <see cref="SetupAttribute"/>, <see cref="BeforeAttribute"/>, <see cref="PathAttribute"/>, <see cref="AfterAttribute"/>,
    /// <see cref="ShutdownAttribute"/>
    /// </para>
    /// </summary>
    /// <param name="type">
    /// <para xml:lang="ru">
    /// Интерфейс, применяемый для строительства
    /// </para>
    /// <para xml:lang="en">
    /// Interface used for construction
    /// </para>
    /// </param>
    /// <param name="helper"></param>
    /// <returns>
    /// <para xml:lang="ru">
    /// Готовый объект
    /// </para>
    /// <para xml:lang="en">
    /// Ready object
    /// </para>
    /// </returns>
    /// <exception cref="ArgumentNullException">
    /// <para xml:lang="ru">
    /// Без хэлпера не работает
    /// </para>
    /// <para xml:lang="en">
    /// Doesn't work without a helper
    /// </para>
    /// </exception>
    public object? BuildOfType(Type type, object helper)
    {
        if (helper is null)
        {
            throw new ArgumentNullException(nameof(helper));
        }
        if (!_helperHandlers.ContainsKey(helper))
        {
            SaveHelper(helper);
        }
        if (_helperMethods[helper.GetType()].TryGetValue(SetUp, out MethodInfo? setup))
        {
            setup?.Invoke(helper, null);
        }
        ValueRequest += _helperHandlers[helper];
        object? result = BuildOfType(type);
        ValueRequest -= _helperHandlers[helper];
        if (_helperMethods[helper.GetType()].TryGetValue(ShutDown, out MethodInfo? shutdown))
        {
            shutdown?.Invoke(helper, null);
        }
        return result;
    }

    /// <summary>
    /// <para xml:lang="ru">
    /// Строит объект с помощью хэндлера, имеющего сигнатуру делегата:
    /// <see cref="ValueRequestEventHandler"/>
    /// Перед вызовом следует подписаться на событие <see cref="ValueRequest"/>
    /// </para>
    /// <para xml:lang="en">
    /// Builds an object using a handler that has a delegate signature:
    /// <see cref="ValueRequestEventHandler"/>
    /// Before calling, subscribe to the event <see cref="ValueRequest"/>
    /// </para>
    /// </summary>
    /// <typeparam name="T">
    /// <para xml:lang="ru">
    /// Интерфейс, применяемый для строительства
    /// </para>
    /// <para xml:lang="en">
    /// Interface used for construction
    /// </para>
    /// </typeparam>
    /// <returns>
    /// <para xml:lang="ru">
    /// Готовый объект
    /// </para>
    /// <para xml:lang="en">
    /// Ready object
    /// </para>
    /// </returns>
    public T? Build<T>() where T : class
    {
        return (T?)BuildOfType(typeof(T));
    }

    /// <summary>
    /// <para xml:lang="ru">
    /// Строит объект с помощью хэндлера, имеющего сигнатуру делегата:
    /// <see cref="ValueRequestEventHandler"/>
    /// Перед вызовом следует подписаться на событие <see cref="ValueRequest"/>
    /// </para>
    /// <para xml:lang="en">
    /// Builds an object using a handler that has a delegate signature:
    /// <see cref="ValueRequestEventHandler"/>
    /// Before calling, subscribe to the event <see cref="ValueRequest"/>
    /// </para>
    /// </summary>
    /// <param name="type">
    /// <para xml:lang="ru">
    /// Интерфейс, применяемый для строительства
    /// </para>
    /// <para xml:lang="en">
    /// Interface used for construction
    /// </para>
    /// </param>
    /// <returns>
    /// <para xml:lang="ru">
    /// Готовый объект
    /// </para>
    /// <para xml:lang="en">
    /// Ready object
    /// </para>
    /// </returns>
    public object? BuildOfType(Type type)
    {
        object? result = null;
        PropertyNode root = new() { TypeNode = _typesForest.GetTypeNode(type) };
        Stack<object?> targets = new();
        Stack<TypeNode?> typeNodes = new();
        ValueRequestEventArgs eventArgs = new();
        List<string> ignoredPaths = new();
        int skipTo = -1;
        int childPosition = 0;
        object[]? key = null;
        eventArgs.RootType = type;
        foreach (ValueRequest request in root.TypeNode.ValueRequests!)
        {

            if (skipTo < 0 || targets.Count <= skipTo)
            {
                skipTo = -1;
                if (!request.PropertyNode.IsLeaf)
                {
                    childPosition = 0;
                    object? target = null;
                    if (request.PropertyNode.TypeNode.Type == type)
                    {
                        target = Target;
                    }
                    if (target is null)
                    {
                        if (_probeObjects.TryGetValue(request.PropertyNode.TypeNode.Type, out object? probe))
                        {
                            _probeObjects.Remove(request.PropertyNode.TypeNode.Type);
                            target = probe;
                        }
                        else
                        {
                            target = _typesForest.ServiceProvider.GetRequiredService(request.PropertyNode.TypeNode.Type);
                        }
                    }
                    if (targets.Count == 0)
                    {
                        result = target;
                    }
                    else
                    {
                        request.PropertyNode.PropertyInfo!.SetValue(targets.Peek(), target);
                    }
                    targets.Push(target);
                    typeNodes.Push(request.PropertyNode.TypeNode);
                    eventArgs.Init(request.PropertyNode, target, request.Path);
                    ValueRequest?.Invoke(eventArgs);
                    if (eventArgs.IsReset || eventArgs.IsCommited)
                    {
                        targets.Pop();
                        if (targets.Count > 0)
                        {
                            request.PropertyNode.PropertyInfo!.SetValue(targets.Peek(), eventArgs.Value);
                        }
                        else
                        {
                            result = eventArgs.Value;
                        }
                        targets.Push(eventArgs.Value);
                        if (eventArgs.IsReset)
                        {
                            _probeObjects.TryAdd(request.PropertyNode.TypeNode.Type, target);
                        }
                        skipTo = targets.Count - 1;
                    }
                }
                else
                {
                    childPosition++;
                    request.PropertyNode.PropertyInfo!.SetValue(targets.Peek(), default);
                    eventArgs.Init(request.PropertyNode, targets.Peek()!, request.Path);
                    ValueRequest?.Invoke(eventArgs);
                    if (!eventArgs.IsCommited)
                    {
                        ignoredPaths.Add($"{eventArgs.NominalType} {eventArgs.Path}");
                    }
                    if (childPosition > 0 && childPosition == typeNodes!.Peek()!.KeysCount)
                    {
                        key = request.PropertyNode.TypeNode.GetKey(targets.Peek()!);
                        if (_objectCache.TryGet(request.PropertyNode.TypeNode.Type, key!, out object? cachedObject))
                        {
                            _probeObjects.TryAdd(request.PropertyNode.TypeNode.Type, targets.Peek()!);
                            targets.Pop();
                            targets.Push(cachedObject);
                            key = null;
                            skipTo = targets.Count - 1;
                        }

                    }
                }
            }
            else
            {
                if (!request.PropertyNode.IsLeaf)
                {
                    targets.Push(null);
                    typeNodes.Push(request.PropertyNode.TypeNode);
                }
            }
            for (int i = request.PopsCount; i < 0; i++)
            {
                object? target = targets.Pop();
                if (key is { } && target is { })
                {
                    _objectCache.Add(typeNodes.Peek()!.Type, key, target!);
                    key = null;
                }
                typeNodes.Pop();
            }
        }
        if (ignoredPaths.Count > 0)
        {
            throw new InvalidOperationException($"path(s) ignored:\n{string.Join("\n", ignoredPaths)}");
        }

        return result;
    }

    /// <summary>
    /// <para xml:lang="ru">
    /// Генерирует скелет для хэндлера, соответствующего применённому интерфейсу
    /// </para>
    /// <para xml:lang="en">
    /// Generates a skeleton for the handler corresponding to the applied interface
    /// </para>
    /// </summary>
    /// <typeparam name="T">
    /// <para xml:lang="ru">
    /// Интерфейс, применяемый для генерации
    /// </para>
    /// <para xml:lang="en">
    /// Interface used to generate
    /// </para>
    /// </typeparam>
    /// <returns>
    /// <para xml:lang="ru">
    /// Исходный код, который можно скопировать и вставить в подходящее место
    /// </para>
    /// <para xml:lang="en">
    /// Source code that can be copied and pasted to a suitable location
    /// </para>
    /// </returns>
    public string GenerateHandlerSkeleton<T>() where T : class
    {
        StringBuilder sb = new();
        sb.Append(@"
(ValueRequestEventArgs args) => {
    switch(args.Path) {");
        void eh(ValueRequestEventArgs args)
        {
            sb.Append(@$"
        case ""{args.Path}"":");
            if (args.IsLeaf)
            {
                sb.Append(@"
            //args.Value = ...;");
                args.IsCommited = true;
            }
            else
            {
                if (args.IsNullable)
                {
                    sb.Append(@"
            //args.Value = ...;
            //args.Value = null;");
                }
                else
                {
                    sb.Append(@"
            //args.Value = ...;
            //args.IsCommited = true;");
                }
            }
            sb.Append(@"
            break;");
        }
        ValueRequest += eh;
        Build<T>();
        ValueRequest -= eh;
        sb.AppendLine(@"
    }
}");
        return sb.ToString();
    }

    /// <summary>
    /// <para xml:lang="ru">
    /// Генерирует скелет для хэлпера, соответствующего применённому интерфейсу
    /// </para>
    /// <para xml:lang="en">
    /// Generates a skeleton for the helper corresponding to the applied interface
    /// </para>
    /// </summary>
    /// <typeparam name="T">
    /// <para xml:lang="ru">
    /// Интерфейс, применяемый для генерации
    /// </para>
    /// <para xml:lang="en">
    /// Interface used to generate
    /// </para>
    /// </typeparam>
    /// <returns>
    /// <para xml:lang="ru">
    /// Исходный код, который можно скопировать и вставить в подходящее место
    /// </para>
    /// <para xml:lang="en">
    /// Source code that can be copied and pasted to a suitable location
    /// </para>
    /// </returns>
    public string GenerateHelperSkeleton<T>() where T : class
    {
        StringBuilder sb = new();
        sb.Append(@"
using Net.Leksi.Dto;

public class HelperSkeleton
{
    [Setup]
    public void Setup()
    {
        throw new NotImplementedException();
    }

    [Shutdown]
    public void Shutdown()
    {
        throw new NotImplementedException();
    }

    [Before]
    public void Before(string path, Type type, object? value, bool isLeaf, bool isNullable)
    {
        throw new NotImplementedException();
    }

    [After]
    public void After(string path, Type type, object? value, bool isLeaf, bool isNullable)
    {
        throw new NotImplementedException();
    }
");
        void eh(ValueRequestEventArgs args)
        {
            sb.Append($@"
    [Path(""{args.Path}"")]
    public object Set_{args.Path.Substring(1).Replace(Slash, Under)}(string path, Type type, object? value, ref bool isCommited)
    {{
        throw new NotImplementedException();
    }}
");
            args.IsCommited = args.IsLeaf;
        }
        ValueRequest += eh;
        Build<T>();
        ValueRequest -= eh;
        sb.Append(@"
}");
        return sb.ToString();
    }

    private void SaveHelper(object helper)
    {
        if (!_helperMethods.ContainsKey(helper.GetType()))
        {
            SaveHelperMethods(helper.GetType());
        }
        Dictionary<string, MethodInfo> methods = _helperMethods[helper.GetType()];
        _helperHandlers[helper] = args =>
        {
            if (methods.TryGetValue(args.Path, out MethodInfo? method))
            {
                Type delegateType = null!;
                try
                {
                    object?[] parameters = null!;
                    if (_helperMethods[helper.GetType()].TryGetValue(Before, out MethodInfo? before))
                    {
                        delegateType = typeof(BeforeOrAfterProcessor);
                        parameters = new object?[] { args.Path, args.NominalType, args.Value, args.IsLeaf, args.IsNullable };
                        before?.Invoke(helper, parameters);
                    }
                    delegateType = typeof(ValueSetter);
                    parameters = new object?[] { args.Path, args.NominalType, args.Value, false };
                    args.Value = method.Invoke(helper, parameters);
                    if (args.IsLeaf 
                        || (!args.IsLeaf && parameters[3] is bool isCommited && isCommited)
                    )
                    {
                        args.IsCommited = true;
                    }
                    if (_helperMethods[helper.GetType()].TryGetValue(After, out MethodInfo? after))
                    {
                        delegateType = typeof(BeforeOrAfterProcessor);
                        parameters = new object?[] { args.Path, args.NominalType, args.IsLeaf, args.Value, args.IsNullable };
                        after?.Invoke(helper, parameters);
                    }
                }
                catch (TargetParameterCountException tgpex)
                {
                    throw new AggregateException(new Exception[] { tgpex, new Exception(@$"{method} parameters count mismatch
possibly reasons:
1) {args.NominalType} is not registered
2) wrong delegate type used, expected: {delegateType.ToString()}") });
                }
                catch (TargetInvocationException tiex)
                {
                    if (tiex.InnerException is NotImplementedException) { }
                    else
                    {
                        throw;
                    }
                }
            }
        };
    }

    private void SaveHelperMethods(Type type)
    {
        Type currentType = type;
        _helperMethods[type] = new Dictionary<string, MethodInfo>();
        Dictionary<string, bool> repeatedMethods = new();
        List<string> delegateMismatches = new();

        while (currentType != typeof(object))
        {
            foreach (MethodInfo methodInfo in currentType!.GetMethods(BindingFlags.NonPublic | BindingFlags.Public | BindingFlags.Instance))
            {
                if (methodInfo.GetCustomAttribute<SetupAttribute>() is { })
                {
                    if (methodInfo.ReturnType != typeof(void) || methodInfo.GetParameters().Length > 0)
                    {
                        delegateMismatches.Add($"{methodInfo} is not a setup void delegate()");
                    }
                    if (!_helperMethods[type].TryAdd(SetUp, methodInfo))
                    {
                        repeatedMethods[SetUp] = true;
                    }
                }
                else if (methodInfo.GetCustomAttribute<ShutdownAttribute>() is { })
                {
                    if (methodInfo.ReturnType != typeof(void) || methodInfo.GetParameters().Length > 0)
                    {
                        delegateMismatches.Add($"{methodInfo} is not a shutdown void delegate()");
                    }
                    if (!_helperMethods[type].TryAdd(ShutDown, methodInfo))
                    {
                        repeatedMethods[ShutDown] = true;
                    }
                }
                else if (methodInfo.GetCustomAttribute<BeforeAttribute>() is { })
                {
                    if (!IsMethodDelegate(methodInfo, typeof(BeforeOrAfterProcessor)))
                    {
                        delegateMismatches.Add($"{methodInfo} is not a delegate {typeof(BeforeOrAfterProcessor)}");
                    }
                    if (!_helperMethods[type].TryAdd(Before, methodInfo))
                    {
                        repeatedMethods[Before] = true;
                    }
                }
                else if (methodInfo.GetCustomAttribute<AfterAttribute>() is { })
                {
                    if (!IsMethodDelegate(methodInfo, typeof(BeforeOrAfterProcessor)))
                    {
                        delegateMismatches.Add($"{methodInfo} is not a delegate {typeof(BeforeOrAfterProcessor)}");
                    }
                    if (!_helperMethods[type].TryAdd(After, methodInfo))
                    {
                        repeatedMethods[After] = true;
                    }
                }
                else
                {
                    ParameterInfo[] parameters0 = methodInfo.GetParameters();
                    foreach (PathAttribute PathAttribute in methodInfo.GetCustomAttributes<PathAttribute>())
                    {
                        if (!_helperMethods[type].TryAdd(PathAttribute.Path, methodInfo))
                        {
                            repeatedMethods[PathAttribute.Path] = true;
                        }
                    }
                }
            }
            currentType = currentType.BaseType!;
        }
        if (delegateMismatches.Count > 0 || repeatedMethods.Count > 0)
        {
            _helperMethods.Remove(type);
            List<Exception> exceptions = new();
            if (delegateMismatches.Count > 0)
            {
                exceptions.Add(new Exception(string.Join("\n", delegateMismatches)));
            }
            if (repeatedMethods.Count > 0)
            {
                exceptions.Add(new Exception(string.Join("\n", repeatedMethods.Select(v => $"{v} method is duplicated"))));
            }
            throw new AggregateException();
        }
    }

    private bool IsMethodDelegate(MethodInfo methodInfo, Type delegateType)
    {
        ParameterInfo[] parameters0 = methodInfo.GetParameters();
        MethodInfo method = delegateType.GetMethod("Invoke")!;
        ParameterInfo[] parameters = method.GetParameters();
        return (
            method.ReturnType == methodInfo.ReturnType
            && parameters0.Length == parameters.Length
            && parameters0.Zip(parameters)
                .All(v =>
                    v.First.ParameterType == v.Second.ParameterType
                    && v.First.IsIn == v.Second.IsIn
                    && v.First.IsOut == v.Second.IsOut));
    }
}
