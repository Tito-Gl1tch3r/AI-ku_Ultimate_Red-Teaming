package net.robinfriedli.jxp.queries;

import java.util.Collection;

import javax.annotation.Nullable;

import net.robinfriedli.jxp.api.XmlElement;

public class QueryResult<E extends XmlElement, C extends Collection<E>> {

    private final C found;

    public QueryResult(C found) {
        this.found = found;
    }

    public C collect() {
        return found;
    }

    @Nullable
    public E getFirstResult() {
        if (found.size() > 0) {
            return found.iterator().next();
        }

        return null;
    }

    public E requireFirstResult() {
        expectAtLeast(1);
        return getFirstResult();
    }

    @Nullable
    public E getOnlyResult() {
        expectAtMost(1);
        return getFirstResult();
    }

    public E requireOnlyResult() {
        expect(1);
        return requireFirstResult();
    }

    public void expect(int i) throws IllegalStateException {
        if (found.size() != i) {
            throw new IllegalStateException("Expected " + i + " elements but found " + found.size());
        }
    }

    public void expectAtLeast(int i) throws IllegalStateException {
        if (found.size() < i) {
            throw new IllegalStateException("Expected at least " + i + " elements but found " + found.size());
        }
    }

    public void expectAtMost(int i) throws IllegalStateException {
        if (found.size() > i) {
            throw new IllegalStateException("Expected at most " + i + " elements but found " + found.size());
        }
    }

    public void expectBetween(int min, int max) throws IllegalStateException {
        try {
            expectAtLeast(min);
            expectAtMost(max);
        } catch (IllegalStateException e) {
            throw new IllegalStateException("Expected " + min + " to " + max + " elements but found " + found.size());
        }
    }

    public long count() {
        return found.size();
    }

}
