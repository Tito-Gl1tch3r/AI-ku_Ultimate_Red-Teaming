using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Simbad.Platform.Core.Utils;
using Simbad.Platform.Core.Substance;
using Simbad.Platform.Persistence.Storage;

namespace Simbad.Platform.Persistence.Converting
{
    public sealed class SimpleParameterlessCtorConverter : IConverter
    {
        private static readonly ConcurrentBag<Type> _safeTypes = new ConcurrentBag<Type>();
        
        public TDao BusinessObject2Dao<TDao>(BusinessObject businessObject) where TDao : Dao
        {
            return Map<BusinessObject, TDao>(businessObject);
        }

        public TBusinessObject Dao2BusinessObject<TBusinessObject>(Dao dao) where TBusinessObject : BusinessObject
        {
            return Map<Dao, TBusinessObject>(dao);
        }

        private static TDest Map<TSrc, TDest>(TSrc src)
        {
            EnsureTypeIsSafe(typeof(TDest));
            
            if (src == null)
            {
                return default(TDest);
            }
            
            var dest = Activator.CreateInstance<TDest>();

            var srcProps = src.GetType().GetProperties(BindingFlags.Public | BindingFlags.Instance);
            var values = new Dictionary<string, object>();

            foreach (var p in srcProps)
            {
                values[p.Name] = p.GetValue(src);
            }

            var destProps = dest.GetType().GetProperties(BindingFlags.Public | BindingFlags.Instance);
            foreach (var p in destProps)
            {
                if (values.ContainsKey(p.Name))
                {
                    p.SetValue(dest, values[p.Name]);
                }
            }

            return dest;
        }
        
        private static void EnsureTypeIsSafe(Type type)
        {
            if (_safeTypes.Contains(type))
            {
                return;
            }

            if (type.IsClass == false)
            {
                throw new InvalidOperationException(
                    $"Cannot create instance of type <{type}>, type is not a class.");
            }

            if (type.IsAbstract)
            {
                throw new InvalidOperationException(
                    $"Cannot create instance of type <{type}>, type is an abstract class.");
            }

            if (type.HasParameterlessCtor() == false)
            {
                throw new InvalidOperationException(
                    $"Cannot create instance of type <{type}>, type has no parameterless ctor.");
            }

            _safeTypes.Add(type);
        }        
    }
}