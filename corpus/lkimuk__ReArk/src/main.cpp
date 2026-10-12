#include "core/AppInitializer.h"

#include <QCoreApplication>
#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlError>
#include <QUrl>

#include <iostream>

int main(int argc, char** argv)
{
    AppInitializer::autoDisableDebugOutput();

    QGuiApplication app(argc, argv);
    QQmlApplicationEngine engine;

    const QStringList arguments = QCoreApplication::arguments();
    const auto initialFileUrl = arguments.size() > 1
        ? QUrl::fromLocalFile(arguments.at(1)).toString()
        : QString();

    AppInitializer initializer(app, engine, initialFileUrl);
    initializer.initializeAll();

    QObject::connect(&engine, &QQmlApplicationEngine::warnings,
                     [](const QList<QQmlError>& warnings) {
                         for (const QQmlError& warning : warnings) {
                             std::cerr << warning.toString().toStdString() << '\n';
                         }
                     });

    const QUrl url(u"qrc:/com/reark/app/main.qml"_qs);
    QObject::connect(&engine, &QQmlApplicationEngine::objectCreated,
                     &app, [url](QObject* obj, const QUrl& objUrl) {
                         if (!obj && url == objUrl) {
                             QCoreApplication::exit(-1);
                         }
                     },
                     Qt::QueuedConnection);

    engine.load(url);
    return app.exec();
}
