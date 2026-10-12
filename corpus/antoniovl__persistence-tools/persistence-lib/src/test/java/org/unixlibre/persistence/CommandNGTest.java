/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package org.unixlibre.persistence;

import static org.testng.Assert.*;
import org.testng.annotations.AfterClass;
import org.testng.annotations.AfterMethod;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

/**
 *
 * @author Antonio Varela Lizardi <antonio@icon.net.mx>
 */
public class CommandNGTest {
    
    @BeforeClass
    public static void setUpClass() throws Exception {
    }

    @AfterClass
    public static void tearDownClass() throws Exception {
    }

    @BeforeMethod
    public void setUpMethod() throws Exception {
    }

    @AfterMethod
    public void tearDownMethod() throws Exception {
    }
    
    @Test
    public void testNullTxType() {
        Command cmd = new Command() {
//            @Override
//            public void execute() {
//                throw new UnsupportedOperationException("Not supported yet."); //To change body of generated methods, choose Tools | Templates.
//            }
            @Override
            public void runWithLocalTx(ExecutorContext ctx) {
                throw new UnsupportedOperationException("Not supported yet."); //To change body of generated methods, choose Tools | Templates.
            }

            @Override
            public void runWithUserTx(ExecutorContext ctx) {
                throw new UnsupportedOperationException("Not supported yet."); //To change body of generated methods, choose Tools | Templates.
            }
        };
        
        cmd.setTransactionType(TransactionTypesEnum.CONTAINER);
        cmd.setTransactionType(null);
        assertEquals(TransactionTypesEnum.CONTAINER, cmd.getTransactionType());
    }
    
    @Test
    public void testRun() {
        final String[] flag = {null};
        Command cmd = new Command() {
//            @Override
//            public void execute() {
//                flag[0] = "EXECUTE";
//            }

            @Override
            public void runWithLocalTx(ExecutorContext ctx) {
                flag[0] = "LOCAL_TX";
            }

            @Override
            public void runWithUserTx(ExecutorContext ctx) {
                flag[0] = "USER_TX";
            }
        };
        
        cmd.setTransactionType(TransactionTypesEnum.CONTAINER);
        try {
            cmd.run(null);
            assertEquals("EXECUTE", flag[0]);
        } catch (UnsupportedOperationException uoe) {
            // ok
        }
        
        cmd.setTransactionType(TransactionTypesEnum.USER);
        cmd.run(null);
        assertEquals("USER_TX", flag[0]);
        
        cmd.setTransactionType(TransactionTypesEnum.LOCAL);
        cmd.run(null);
        assertEquals("LOCAL_TX", flag[0]);
    }
}
