using System;
using System.Collections.Generic;
using System.Linq;
using System.Linq.Expressions;
using Nervestaple.EntityFrameworkCore.Models.Entities;
using Nervestaple.EntityFrameworkCore.Models.Parameters;

namespace Nervestaple.EntityFrameworkCore.Repositories {

    /// <summary>
    /// Provides a builder that accepts a list of sort parameters and applies
    /// a set of matching sort constraints to the provided enumerable.
    /// </summary>
    /// <typeparam name="TEntity">Type of Entity</typeparam>
    /// <typeparam name="TId">Type of unique identifier for the Entity</typeparam>
    public class SortBuilder<TEntity, TId> 
        where TEntity: Entity<TId>
        where TId: struct {        
        
        /// <summary>
        /// Combines the queryable with the provided search parameters.
        /// <param name="enumerable">Queryable to refine</param>
        /// <param name="sorts">List of sort parameters</param>
        /// </summary>
        public IQueryable<TEntity> GetSorts(IQueryable<TEntity> enumerable, IEnumerable<SortParameter> sorts) {

            if(sorts != null) {
                
                foreach(SortParameter sortParam in sorts) {

                    // the type of queryable
                    ParameterExpression type = Expression.Parameter(typeof(TEntity), string.Empty);

                    // the property we want to sort on
                    MemberExpression property = Expression.Property(type, sortParam.Field);

                    // special-case handling for ID sorts
                    if (sortParam.Field.ToLower().Equals("id")) {
                    
                        // entities know which attribute maps to their primary key
                        if(typeof(TEntity).IsSubclassOf(typeof(Entity<TId>))) {
                            var instanceThis = Activator.CreateInstance(typeof(TEntity));

                            try {
                                string idAttribute = (string) (typeof(TEntity)).GetMethod("IdAttribute").Invoke(instanceThis, null);
                                property = Expression.Property(type, idAttribute); 
                            } catch (Exception) {
                                // fall back to the default attribute name
                            }
                        }
                    }

                    // lamba expressor for our sort
                    LambdaExpression sortLambda = Expression.Lambda(property, type);

                    // string with our sort method
                    string orderMethod = sortParam.Desc ? "OrderByDescending" : "OrderBy";

                    // create an expression to call the order method on our queryable's field
                    MethodCallExpression callExpression = Expression.Call(
                        typeof(Queryable),
                        orderMethod,
                        new[] {typeof(TEntity), property.Type},
                        enumerable.Expression,
                        Expression.Quote(sortLambda));
                    enumerable = enumerable.Provider.CreateQuery<TEntity>(callExpression);
                }
            }

            return enumerable;
        }
    }
}