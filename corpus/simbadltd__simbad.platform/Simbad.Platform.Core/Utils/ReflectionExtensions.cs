using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Reflection;

namespace Simbad.Platform.Core.Utils
{
    public static class ReflectionExtensions
    {
        public static bool IsGenericEnumerable(this Type type)
        {
            return type.GetTypeInfo().IsGenericType && type.GetGenericTypeDefinition() == typeof(IEnumerable<>);
        }

        public static bool IsNullable(this Type type)
        {
            return
                type != null &&
                type.GetTypeInfo().IsGenericType &&
                type.GetGenericTypeDefinition() == typeof(Nullable<>);
        }

        public static TValue GetAttributeValue<TAttribute, TValue>(
            this Type type,
            Func<TAttribute, TValue> valueSelector)
            where TAttribute : Attribute
        {
            var attr = type.GetTypeInfo().GetCustomAttributes(typeof(TAttribute), true).FirstOrDefault() as TAttribute;
            if (attr != null)
            {
                return valueSelector(attr);
            }

            return default(TValue);
        }

        public static bool HasAttribute<TAttributeType>(this Type type)
        {
            return type.HasAttribute(typeof(TAttributeType));
        }

        public static bool HasAttribute(this Type type, Type attributeType)
        {
            if (type == null)
            {
                return false;
            }

            return type.GetTypeInfo().GetCustomAttributes(attributeType, false).Any();
        }

        public static IEnumerable<Type> GetDerivedTypes(this Type baseType, Predicate<TypeInfo> predicate)
        {
            if (baseType == null)
            {
                return Enumerable.Empty<Type>();
            }

            predicate = predicate ?? (t => true);

            var types = baseType.GetTypeInfo().Assembly.ExportedTypes;

            Func<TypeInfo, bool> genericTypeSelector = t =>
                t.BaseType != null &&
                t.BaseType.GetTypeInfo().IsGenericType &&
                t.BaseType.GetGenericTypeDefinition() == baseType;

            Func<TypeInfo, bool> nonGenericTypeSelector = baseType.GetTypeInfo().IsAssignableFrom;

            var typeSelector = baseType.GetTypeInfo().IsGenericType ? genericTypeSelector : nonGenericTypeSelector;

            return types.Where(t => typeSelector(t.GetTypeInfo()) && predicate(t.GetTypeInfo())).ToList();
        }

        public static bool IsDerivedFrom(this Type type, Type superType)
        {
            if (type == null)
                throw new ArgumentNullException(nameof(type));
            if (superType == null)
                throw new ArgumentNullException(nameof(superType));

            if (type == superType)
                return true;

            var typeInfo = type.GetTypeInfo();
            var superTypeInfo = superType.GetTypeInfo();

            if (superTypeInfo.IsAssignableFrom(typeInfo))
                return true;

            // For non-generic types, any interface and base class relationship is handled by IsAssignableFrom
            if (!superTypeInfo.IsGenericType)
                return false;

            // For generic types, it's more complicated because for example ICollection<> is not assignable from List<int> just because you can't make a variable of ICollection<>

            if (superTypeInfo.IsGenericTypeDefinition)
            {
                var superTypeIsOpenGenericInterface = superTypeInfo.IsInterface;
                if (superTypeIsOpenGenericInterface)
                {
                    var implementsSuperInterface = type.GetTypeInfo()
                        .ImplementedInterfaces.Concat(new[] { type })
                        .Any(x => x.IsConstructedGenericType && x.GetGenericTypeDefinition() == superType);

                    if (implementsSuperInterface)
                    {
                        return true;
                    }
                }
                else
                {
                    Debug.Assert(superTypeInfo.IsClass || superTypeInfo.IsValueType, "superTypeInfo.IsClass || superTypeInfo.IsValueType");

                    if (WalkBaseTypeChain(typeInfo).Any(x => x.IsGenericType && x.GetGenericTypeDefinition() == superType))
                    {
                        return true;
                    }
                }
            }

            return false;
        }

        public static object GetDefaultValue(this Type type)
        {
            if (type == null)
                throw new ArgumentNullException(nameof(type));

            var typeInfo = type.GetTypeInfo();
            if (typeInfo.IsValueType && !IsNullableValueType(type))
            {
                return Activator.CreateInstance(type);
            }

            return null;
        }

        private static bool IsNullableValueType(Type type)
        {
            return Nullable.GetUnderlyingType(type) != null;
        }

        private static IEnumerable<TypeInfo> WalkBaseTypeChain(TypeInfo typeInfo)
        {
            var current = typeInfo.BaseType;
            while (current != null)
            {
                var currentTypeInfo = current.GetTypeInfo();
                yield return currentTypeInfo;

                current = currentTypeInfo.BaseType;
            }
        }

        public static Type GetCollectionItemType(this Type type)
        {
            if (type == null)
                throw new ArgumentNullException(nameof(type));

            if (type == typeof(string)) return null;

            // Collection type might or might not be generic itself.
            // However, we know it implements IEnumerable<T>.
            // So, find that interface
            var possibleInterfaces = type.GetTypeInfo().ImplementedInterfaces.ToList();
            possibleInterfaces.Add(type);
            
            var collectionInterface =
                possibleInterfaces.SingleOrDefault(x => x.GetTypeInfo().IsGenericType && x.GetGenericTypeDefinition() == typeof(IEnumerable<>));

            if (collectionInterface == null) return null;

            // and get its type argument
            var itemType = collectionInterface.GenericTypeArguments.Single();

            return itemType;
        }

        public static bool IsInstanceOfType(this Type type, object value)
        {
            if (type == null)
                throw new ArgumentNullException(nameof(type));
            if (value == null)
                return false;

            return value.GetType().IsDerivedFrom(type);
        }

        public static bool HasParameterlessCtor(this Type type)
        {
            return type.GetTypeInfo().DeclaredConstructors.Any(
                x =>
                {
                    var parameters = x.GetParameters();
                    var isParameterlessCtor = parameters.Length == 0;
                    return isParameterlessCtor && x.IsStatic == false;
                });
        }

        public static T InvokeGenericMethod<T>(this object target, Type typeArgument, string methodName, params object[] args)
        {
            return (T)InvokeGenericMethod(target, typeArgument, methodName, args);
        }

        public static object InvokeGenericMethod(this object target, Type typeArgument, string methodName, params object[] args)
        {
            var open = target.GetType().GetRuntimeMethods().Single(m => m.IsGenericMethod && m.Name == methodName);
            var genericMethod = open.MakeGenericMethod(typeArgument);
            return genericMethod.Invoke(target, args);
        }

        public static void InvokeMethodForEach(this object target, string methodName, ArrayList items)
        {
            var method = target.GetType().GetRuntimeMethods().Single(m => m.Name == methodName);

            foreach (var arg in items)
            {
                method.Invoke(target, new[] {arg});
            }
        }

    }
}