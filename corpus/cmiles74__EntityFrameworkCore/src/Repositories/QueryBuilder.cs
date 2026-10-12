using System;
using System.Collections.Generic;
using System.Linq;
using System.Linq.Expressions;
using System.Reflection;
using Nervestaple.EntityFrameworkCore.Models.Criteria;
using Nervestaple.EntityFrameworkCore.Models.Entities;
using Nervestaple.EntityFrameworkCore.Models.Parameters;

namespace Nervestaple.EntityFrameworkCore.Repositories {

    /// <summary>
    /// Provides a builder that accepts a data object with search parameters
    /// and applies a set of matching query constraints to the enumerable.
    /// </summary>
    /// <typeparam name="TEntity">Type of Entity</typeparam>
    /// <typeparam name="TId">Type of unique identifier for the Entity</typeparam>
    public class QueryBuilder<TEntity, TId> 
        where TEntity: IEntity<TId>
        where TId: struct {
    
        /// <summary>
        /// Combines the provided queryable with a query derived from the provided criteria.
        /// <param name="queryable">Queryable which will be refined</param>
        /// <param name="criteria">Criteria used to refine the queryable</param>
        /// </summary>
        public static IQueryable<TEntity> GetResults(IQueryable<TEntity> queryable, ISearchCriteria<TEntity, TId> criteria) {

            // ingore query properties with ignore attribute or that have a null value
            IEnumerable<PropertyInfo> properties = criteria.GetType().GetProperties().Where(
                p => p.GetCustomAttributes().FirstOrDefault(a => a.GetType().Equals(typeof(QueryIgnore))) == null 
                    && p.GetValue(criteria) != null);

            foreach(PropertyInfo property in properties) {

                if(property.PropertyType.Equals(typeof(string))) {
                    
                    queryable = AddWhereContains(queryable, criteria, property);
                } else if(property.PropertyType.Equals(typeof(DateRangeParameter))) {
                    queryable = AddBetweenDateRange(queryable, criteria, property);
                } else if(property.PropertyType.Equals(typeof(DecimalRangeParameter))) {
                    queryable = AddBetweenDecimalRange(queryable, criteria, property);
                } else {
                    queryable = AddEquals(queryable, criteria, property);
                }
            }

            return queryable;
        }

        private static ParameterExpression GetTargetType() {
            return Expression.Parameter(typeof(TEntity), string.Empty);
        }

        private static MemberExpression GetTargetField(ParameterExpression targetType, string propertyName) {

            // the field on the queryable
            return Expression.Property(targetType, propertyName);
        }

        private static IQueryable<TEntity> AddWhereContains(IQueryable<TEntity> queryable, ISearchCriteria<TEntity, TId> criteria, PropertyInfo source) {
            
            // the type of queryable
            ParameterExpression targetType = GetTargetType();

            // add a contains clause
            MethodInfo method = typeof(string).GetMethod("Contains", new[] { typeof(string) });

            // the value from the query as a string
            ConstantExpression value = Expression.Constant(source.GetValue(criteria).ToString(), typeof(string));

            // method call to compare the queryable's value to ours
            MethodCallExpression test = Expression.Call(GetTargetField(targetType, source.Name), method, value);

            // lambda that expresses our comparison
            Expression<Func<TEntity, bool>> lambda = Expression.Lambda<Func<TEntity, bool>>(test, targetType);

            return queryable.Where(lambda);
        }

        private static IQueryable<TEntity> AddBetweenDateRange(IQueryable<TEntity> queryable, ISearchCriteria<TEntity, TId> criteria, PropertyInfo source) {

            // the type of queryable
            ParameterExpression targetType = GetTargetType();

            // expression to convert our queryable's value to match our own
            UnaryExpression convertedField = Expression.Convert(GetTargetField(targetType, source.Name), typeof(DateTime));

            // add a between dates clause
            DateRangeParameter dateRangeParam = (DateRangeParameter) source.GetValue(criteria);
            if(dateRangeParam.Start.HasValue && dateRangeParam.End.HasValue) {

                // extract our date range start and end
                DateTime start = dateRangeParam.Start.Value;
                DateTime end = dateRangeParam.End.Value;

                // our starting value
                ConstantExpression startExpression = Expression.Constant(start, typeof(DateTime));

                // compare the queryable's value to our start
                BinaryExpression testStart = Expression.GreaterThanOrEqual(convertedField, startExpression);

                // our ending value
                ConstantExpression endExpression = Expression.Constant(end, typeof(DateTime));

                // compare the queryable's value to our end
                BinaryExpression testEnd = Expression.LessThanOrEqual(convertedField, endExpression);

                // lambda expressions for our tests
                Expression<Func<TEntity, bool>> lambdaStart = Expression.Lambda<Func<TEntity, bool>>(testStart, targetType);
                Expression<Func<TEntity, bool>> lambdaEnd = Expression.Lambda<Func<TEntity, bool>>(testEnd, targetType);
                
                queryable = queryable.Where(lambdaStart).Where(lambdaEnd);
            } else if(dateRangeParam.Start.HasValue) {

                // extract our date range start and end
                DateTime start = dateRangeParam.Start.Value;

                // our starting value
                ConstantExpression startExpression = Expression.Constant(start, typeof(DateTime));

                // compare the queryable's value to our start
                BinaryExpression testStart = Expression.GreaterThanOrEqual(convertedField, startExpression);

                // lambda expressions for our tests
                Expression<Func<TEntity, bool>> lambda = Expression.Lambda<Func<TEntity, bool>>(testStart, targetType);

                queryable = queryable.Where(lambda);
            } else if(dateRangeParam.End.HasValue) {

                // extract our date range start and end
                DateTime end = dateRangeParam.End.Value;

                // our ending value
                ConstantExpression endExpression = Expression.Constant(end, typeof(DateTime));

                // compare the queryable's value to our end
                BinaryExpression testEnd = Expression.LessThanOrEqual(convertedField, endExpression);

                // lambda expressions for our tests
                Expression<Func<TEntity, bool>> lambda = Expression.Lambda<Func<TEntity, bool>>(testEnd, targetType);
                
                queryable = queryable.Where(lambda);
            } else {
                
                // our matching value
                ConstantExpression endExpression = Expression.Constant(null, typeof(DateTime?));
                
                // expression to convert our queryable's value to match our own
                UnaryExpression convertedFieldNullable = 
                    Expression.Convert(GetTargetField(targetType, source.Name), typeof(DateTime?));

                // compare the queryable's value to our end
                BinaryExpression testEnd = Expression.Equal(convertedFieldNullable, endExpression);

                // lambda expressions for our tests
                Expression<Func<TEntity, bool>> lambda = Expression.Lambda<Func<TEntity, bool>>(testEnd, targetType);
                
                queryable = queryable.Where(lambda);
            }

            return queryable;
        }

        private static IQueryable<TEntity> AddBetweenDecimalRange(IQueryable<TEntity> queryable, ISearchCriteria<TEntity, TId> criteria, PropertyInfo source) {

            // the type of queryable
            ParameterExpression targetType = GetTargetType();

            // expression to convert our queryable's value to match our own
            UnaryExpression convertedField = Expression.Convert(GetTargetField(targetType, source.Name), typeof(decimal));

            // add a between decimals clause
            DecimalRangeParameter decimalRangeParam = (DecimalRangeParameter) source.GetValue(criteria);
            if(decimalRangeParam.Start.HasValue && decimalRangeParam.End.HasValue) {

                // extract our date range start and end
                decimal start = decimalRangeParam.Start.Value;
                decimal end = decimalRangeParam.End.Value;

                // our starting value
                ConstantExpression startExpression = Expression.Constant(start, typeof(decimal));

                // compare the queryable's value to our start
                BinaryExpression testStart = Expression.GreaterThanOrEqual(convertedField, startExpression);

                // our ending value
                ConstantExpression endExpression = Expression.Constant(end, typeof(decimal));

                // compare the queryable's value to our end
                BinaryExpression testEnd = Expression.LessThanOrEqual(convertedField, endExpression);

                // lambda expressions for our tests
                Expression<Func<TEntity, bool>> lambdaStart = Expression.Lambda<Func<TEntity, bool>>(testStart, targetType);
                Expression<Func<TEntity, bool>> lambdaEnd = Expression.Lambda<Func<TEntity, bool>>(testEnd, targetType);
                
                queryable = queryable.Where(lambdaStart).Where(lambdaEnd);
            } else if(decimalRangeParam.Start.HasValue) {

                // extract our date range start and end
                decimal start = decimalRangeParam.Start.Value;

                // our starting value
                ConstantExpression startExpression = Expression.Constant(start, typeof(decimal));

                // compare the queryable's value to our start
                BinaryExpression testStart = Expression.GreaterThanOrEqual(convertedField, startExpression);

                // lambda expressions for our tests
                Expression<Func<TEntity, bool>> lambda = Expression.Lambda<Func<TEntity, bool>>(testStart, targetType);

                queryable = queryable.Where(lambda);
            } else if(decimalRangeParam.End.HasValue) {

                // extract our date range start and end
                decimal end = decimalRangeParam.End.Value;

                // our ending value
                ConstantExpression endExpression = Expression.Constant(end, typeof(decimal));

                // compare the queryable's value to our end
                BinaryExpression testEnd = Expression.LessThanOrEqual(convertedField, endExpression);

                // lambda expressions for our tests
                Expression<Func<TEntity, bool>> lambda = Expression.Lambda<Func<TEntity, bool>>(testEnd, targetType);
                
                queryable = queryable.Where(lambda);
            } else {
                
                // our matching value
                ConstantExpression endExpression = Expression.Constant(null, typeof(decimal?));
                
                // expression to convert our queryable's value to match our own
                UnaryExpression convertedFieldNullable = 
                    Expression.Convert(GetTargetField(targetType, source.Name), typeof(decimal?));

                // compare the queryable's value to our end
                BinaryExpression testEnd = Expression.Equal(convertedFieldNullable, endExpression);

                // lambda expressions for our tests
                Expression<Func<TEntity, bool>> lambda = Expression.Lambda<Func<TEntity, bool>>(testEnd, targetType);

                return queryable.Where(lambda);
            }

            return queryable;
        }

        private static IQueryable<TEntity> AddEquals(IQueryable<TEntity> queryable, ISearchCriteria<TEntity, TId> criteria, PropertyInfo source) {
            
            // the type of queryable
            ParameterExpression targetType = GetTargetType();

            // the field we're querying against
            var field = GetTargetField(targetType, source.Name);
            
            // we handle GUID instances differently
            if (field.Type == typeof(Guid) || field.Type == typeof(Guid?)) {

                // get a handle on our Guid? or Guid, use an empty GUID if null
                object sourceValue = source.GetValue(criteria);
                Guid sourceGuid = Guid.Empty;
                if (sourceValue != null) {
                    if (sourceValue is Guid?) {
                        sourceGuid = (((Guid?) sourceValue).HasValue ? ((Guid?) sourceValue).Value : Guid.Empty);
                    } else {
                        sourceGuid = (Guid) sourceValue;
                    }
                }

                // expression with our value to match
                var value = Expression.Constant(sourceGuid, typeof(Guid));
            
                // add an equals clause to match a GUID
                MethodInfo method = typeof(Guid).GetMethod("Equals", new[] { typeof(Guid) });
                
                // ensure that the queryable has a GUID, default to empty GUID
                var fieldNotNull = Expression.Coalesce(
                    Expression.Property(targetType, source.Name),
                    Expression.Constant(Guid.Empty));

                // method call to compare the queryable's value to ours
                MethodCallExpression test = Expression.Call(fieldNotNull, method, value);

                // lambda that expresses our comparison
                return queryable.Where(Expression.Lambda<Func<TEntity, bool>>(test, targetType));
            } else {

                // the value from the query as an object
                var value = 
                    Expression.Convert(Expression.Constant(source.GetValue(criteria)), field.Type);

                // compare the queryable's value to ours
                var test = Expression.Equal(field, value);

                // lambda that expresses our comparison
                return queryable.Where(Expression.Lambda<Func<TEntity, bool>>(test, targetType));
            }
        }
    }
}