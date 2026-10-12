using System;
using System.Collections.Generic;
using Simbad.Platform.Core.Substance;
using Simbad.Platform.Persistence.Storage;

namespace Simbad.Platform.Persistence.Converting
{
    public static class Mapping
    {
        private static readonly Dictionary<Type, Type> _businessObject2Dao = new Dictionary<Type, Type>();

        private static readonly Dictionary<Type, Type> _dao2BusinessObject = new Dictionary<Type, Type>();

        public static Type DaoTypeFor(Type businessObjectType)
        {
            if (_businessObject2Dao.ContainsKey(businessObjectType) == false)
            {
                throw new InvalidOperationException($"There is no mapping for business object type <{businessObjectType}>");
            }

            return _businessObject2Dao[businessObjectType];
        }

        public static Type BusinessObjectTypeFor(Type daoType)
        {
            if (_dao2BusinessObject.ContainsKey(daoType) == false)
            {
                throw new InvalidOperationException($"There is no mapping for dao type <{daoType}>");
            }

            return _dao2BusinessObject[daoType];
        }

        public static MappingConfiguration Configure()
        {
            return new MappingConfiguration();
        }

        public sealed class MappingConfiguration
        {
            public MappingConfiguration Add<TBusinessObject, TDao>()
                where TDao : Dao where TBusinessObject : BusinessObject
            {
                var businessObjectType = typeof(TBusinessObject);
                var daoType = typeof(TDao);

                if (_businessObject2Dao.ContainsKey(businessObjectType) && _businessObject2Dao[businessObjectType] != daoType)
                {
                    throw new InvalidOperationException($"We already have mapping for <{businessObjectType}>");
                }

                if (_dao2BusinessObject.ContainsKey(daoType) && _dao2BusinessObject[daoType] != businessObjectType)
                {
                    throw new InvalidOperationException($"We already have mapping for <{daoType}>");
                }

                _businessObject2Dao[businessObjectType] = daoType;
                _dao2BusinessObject[daoType] = businessObjectType;

                return this;
            }
        }
    }
}