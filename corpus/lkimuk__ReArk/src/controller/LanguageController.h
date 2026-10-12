#ifndef REARK_LANGUAGE_CONTROLLER_H
#define REARK_LANGUAGE_CONTROLLER_H

#include <QObject>
#include <QString>

class QQmlEngine;
class Translator;

class LanguageController : public QObject {
    Q_OBJECT
    Q_PROPERTY(QString currentLanguage READ currentLanguage NOTIFY languageChanged)
    Q_PROPERTY(bool hasUserLanguage READ hasUserLanguage NOTIFY languageChanged)

public:
    explicit LanguageController(QQmlEngine* engine, QObject* parent = nullptr);

    QString currentLanguage() const;
    bool hasUserLanguage() const;

    Q_INVOKABLE bool switchLanguage(const QString& locale);
    Q_INVOKABLE void clearLanguageOverride();
    Q_INVOKABLE void resetLanguage();

signals:
    void languageChanged();

private:
    bool applyLanguage(const QString& locale);
    static QString normalizedSupportedLocale(const QString& locale);
    static QString systemLanguage();

    Translator* translator_ = nullptr;
    QString currentLanguage_ = QStringLiteral("en_US");
    bool hasUserLanguage_ = false;
};

#endif // REARK_LANGUAGE_CONTROLLER_H
