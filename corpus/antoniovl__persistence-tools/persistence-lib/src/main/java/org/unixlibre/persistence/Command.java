/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package org.unixlibre.persistence;

import java.io.Serializable;
import java.util.function.Function;

/**
 *
 * @author Antonio Varela Lizardi <antonio@icon.net.mx>
 */
public abstract class Command<T> implements Serializable {
    
    private TransactionTypesEnum transactionType = TransactionTypesEnum.LOCAL;
    
    public abstract void runWithLocalTx(ExecutorContext ctx);
    public abstract void runWithUserTx(ExecutorContext ctx);
   
    private Function<ExecutorContext, T> implementation = (executorContext) -> {
        throw new UnsupportedOperationException("Not supported yet");
    };

    private T result;

    public Command() {
    }

    public Command(Function<ExecutorContext, T> implementation) {
        this.implementation = implementation;
    }

    protected void execute(ExecutorContext executorContext) {
        if (implementation != null) {
            init();
            result = implementation.apply(executorContext);
            destroy();
        }
    }
    
    /**
     * Initialize any required resources.
     */
    public void init() {
    }
    
    /**
     * Clean up any resources from init().
     */
    public void destroy() {
    }
    
    /**
     * Method to be invoked by the CommandExecutor.
     */
    public void run(ExecutorContext ctx) {
        
        switch (transactionType) {
            case CONTAINER:
                // The transaction it's controlled elswehere, no need to
                // initialize/commit/rollback.
                execute(ctx);
                break;
            case USER:
                runWithUserTx(ctx);
                break;
            default:
                runWithLocalTx(ctx);
                break;
        }
    }
    
    public TransactionTypesEnum getTransactionType() {
        return transactionType;
    }

    public void setTransactionType(TransactionTypesEnum transactionType) {
        if (transactionType != null) {
            // can't be null
            this.transactionType = transactionType;
        }
    }

    protected Function<ExecutorContext, T> getImplementation() {
        return implementation;
    }

    public void setImplementation(Function<ExecutorContext, T> implementation) {
        this.implementation = implementation;
    }

    public T getResult() {
        return result;
    }

    protected void setResult(T result) {
        this.result = result;
    }
}
