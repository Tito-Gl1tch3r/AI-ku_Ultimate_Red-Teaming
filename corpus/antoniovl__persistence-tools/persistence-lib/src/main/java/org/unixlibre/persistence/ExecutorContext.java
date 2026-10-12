/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package org.unixlibre.persistence;

import java.io.Serializable;

/**
 *
 * @author Antonio Varela Lizardi <antonio@icon.net.mx>
 */
public class ExecutorContext implements Serializable {

    private boolean rollbackOnApplicationException = false;
    private boolean supportsNestedTransaction = false;

    public ExecutorContext() {
    }

    public ExecutorContext(boolean rollbackOnApplicationException, boolean supportsNestedTransaction) {
        this.rollbackOnApplicationException = rollbackOnApplicationException;
        this.supportsNestedTransaction = supportsNestedTransaction;
    }

    public boolean isRollbackOnApplicationException() {
        return rollbackOnApplicationException;
    }

    public void setRollbackOnApplicationException(boolean rollbackOnApplicationException) {
        this.rollbackOnApplicationException = rollbackOnApplicationException;
    }

    public boolean isSupportsNestedTransaction() {
        return supportsNestedTransaction;
    }

    public void setSupportsNestedTransaction(boolean supportsNestedTransaction) {
        this.supportsNestedTransaction = supportsNestedTransaction;
    }
}
