package net.robinfriedli.jxp.persist;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerException;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;

import net.robinfriedli.jxp.exceptions.CommitException;
import net.robinfriedli.jxp.exceptions.PersistException;
import org.w3c.dom.Document;
import org.xml.sax.SAXException;

public class StaticXmlParser {

    public static void writeToFile(Context context) throws CommitException {
        if (!context.isPersistent()) {
            throw new CommitException("Context is not persistent. Cannot write to file");
        }

        Document doc = context.getDocument();
        try {
            TransformerFactory transformerFactory = TransformerFactory.newInstance();
            Transformer transformer = transformerFactory.newTransformer();
            DOMSource source = new DOMSource(doc);
            @SuppressWarnings("ConstantConditions")
            StreamResult result = new StreamResult(context.getFile());

            transformer.transform(source, result);
        } catch (TransformerException e) {
            throw new CommitException("Exception while writing to file", e);
        }
    }

    public static Document parseDocument(File xml) {
        try {
            DocumentBuilderFactory dbFactory = DocumentBuilderFactory.newInstance();
            DocumentBuilder dBuilder = dbFactory.newDocumentBuilder();
            return dBuilder.parse(xml);
        } catch (IOException | SAXException | ParserConfigurationException e) {
            throw new PersistException("Exception while parsing document", e);
        }
    }


    public static Document parseDocument(InputStream xml) {
        try {
            DocumentBuilderFactory dbFactory = DocumentBuilderFactory.newInstance();
            DocumentBuilder dBuilder = dbFactory.newDocumentBuilder();
            return dBuilder.parse(xml);
        } catch (IOException | SAXException | ParserConfigurationException e) {
            throw new PersistException("Exception while parsing document", e);
        }
    }

}
