using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using Simbad.Platform.Core;
using Simbad.Platform.Core.Utils;
using Simbad.Platform.Core.Substance;
using Simbad.Platform.Core.Substance.IdGeneration;
using Simbad.Platform.Core.Substance.Registration;
using Simbad.Platform.Persistence.Converting;
using Simbad.Platform.Persistence.Storage;

namespace Simbad.Platform.Persistence
{
    public sealed class Repository<TBusinessObject> : IRepository<TBusinessObject> where TBusinessObject : BusinessObject
    {
        private const string Dao2BusinessObjectMethodName = "Dao2BusinessObject";
        
        private const string BusinessObject2DaoMethodName = "BusinessObject2Dao";

        private static Type DaoType => Mapping.DaoTypeFor(typeof(TBusinessObject));

        private readonly object _syncRoot = new object();

        private readonly Dictionary<Guid, TBusinessObject> _cache = new Dictionary<Guid, TBusinessObject>();

        private readonly IStorageAdapter _storageAdapter;

        private readonly IUnitOfWork _unitOfWork;

        private bool _allFetched;

        public Repository(IUnitOfWork unitOfWork)
        {
            _storageAdapter = Global.Ioc.Resolver.Resolve<IStorageAdapter>();
            _unitOfWork = unitOfWork;
        }

        public TBusinessObject Get(Guid id)
        {
            lock (_syncRoot)
            {
                return GetOrAdd(
                    id,
                    guid =>
                    {
                        var model = _storageAdapter.Transaction(tw => tw.Fetch(guid, DaoType));
                        var converter = CreateConverter();
                        var result = converter.Dao2BusinessObject<TBusinessObject>(model);

                        return result;
                    });
            }
        }

        public IReadOnlyCollection<TBusinessObject> GetAll()
        {
            lock (_syncRoot)
            {
                if (_allFetched)
                {
                    return _cache.Values.ToList();
                }

                var all = _storageAdapter.Transaction(t => t.FetchAll(DaoType));

                var converter = CreateConverter();
                var result = all.Select(x => converter.Dao2BusinessObject<TBusinessObject>(x)).ToList();

                RefreshCache(result);
                _allFetched = true;

                return result;
            }
        }

        public void Delete(Guid id)
        {
            lock (_syncRoot)
            {
                _unitOfWork.Delete(id, DaoType);
                InvalidateCache(id);
            }
        }

        public void DeleteAll()
        {
            lock (_syncRoot)
            {
                _unitOfWork.DeleteAll(DaoType);
                InvalidateCache();
            }
        }

        public TBusinessObject FindSingle(Func<TBusinessObject, bool> predicate)
        {
            lock (_syncRoot)
            {
                var aggregate = GetAll().SingleOrDefault(predicate);
                return aggregate;
            }
        }

        public ICollection<TBusinessObject> FindAll(Func<TBusinessObject, bool> predicate)
        {
            lock (_syncRoot)
            {
                var aggregates = GetAll().Where(predicate).ToList();
                return aggregates;
            }
        }

        public TBusinessObject Clone(TBusinessObject source)
        {
            var converter = CreateConverter();

            var dao = converter.InvokeGenericMethod(DaoType, BusinessObject2DaoMethodName, source);
            var clone = converter.InvokeGenericMethod(typeof(TBusinessObject), Dao2BusinessObjectMethodName, dao) as TBusinessObject;

            Debug.Assert(clone != null);
            clone.Id = IdGenerator.NewId();

            return clone;
        }

        public void Save(TBusinessObject businessObject)
        {
            // [kk] here we can check businessObject consistency in the future

            lock (_syncRoot)
            {
                var events = businessObject.ExtractEvents();
                _unitOfWork.TrackEvents(events);

                var converter = CreateConverter();
                var model = converter.InvokeGenericMethod(DaoType, BusinessObject2DaoMethodName, businessObject);

                _unitOfWork.Save(model, DaoType);

                RefreshCache(businessObject);
            }
        }

        private static IConverter CreateConverter()
        {
            return Global.Ioc.Resolver.Resolve<IConverter>();
        }

        private TBusinessObject GetOrAdd(Guid id, Func<Guid, TBusinessObject> factory)
        {
            if (_cache.ContainsKey(id))
            {
                return _cache[id];
            }

            var result = factory(id);
            RefreshCache(result);

            return result;
        }

        private void RefreshCache(IEnumerable<TBusinessObject> aggregates)
        {
            foreach (var aggregate in aggregates)
            {
                RefreshCache(aggregate);
            }
        }

        private void RefreshCache(TBusinessObject aggregate)
        {
            if (aggregate == null) return;

            _cache[aggregate.Id] = aggregate;
        }

        private void InvalidateCache(Guid id)
        {
            if (_cache.ContainsKey(id) == false)
            {
                return;
            }

            _cache.Remove(id);
            _allFetched = false;
        }

        private void InvalidateCache()
        {
            _cache.Clear();
            _allFetched = false;
        }
    }
}