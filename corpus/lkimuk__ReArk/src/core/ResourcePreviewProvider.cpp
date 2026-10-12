#include "core/ResourcePreviewProvider.h"

#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QMutexLocker>
#include <QStandardPaths>
#include <QUrl>
#include <QUuid>

#include <utility>

ResourcePreviewProvider::ResourcePreviewProvider()
    : QQuickImageProvider(QQuickImageProvider::Image)
{
}

QString ResourcePreviewProvider::storeImage(const QByteArray& bytes)
{
    const QString id = QUuid::createUuid().toString(QUuid::WithoutBraces);
    QMutexLocker locker(&mutex_);
    images_.insert(id, bytes);
    return QStringLiteral("image://rearkResources/%1").arg(id);
}

QString ResourcePreviewProvider::storeMediaFile(const QString& sourceName, const QByteArray& bytes)
{
    const QString extension = QFileInfo(sourceName).suffix().isEmpty()
        ? QStringLiteral("bin")
        : QFileInfo(sourceName).suffix().toLower();
    const QString fileName = QStringLiteral("%1.%2")
        .arg(QUuid::createUuid().toString(QUuid::WithoutBraces), extension);
    const QString directory = cacheDirectory();
    QDir().mkpath(directory);

    const QString filePath = QDir(directory).filePath(fileName);
    QFile file(filePath);
    if (!file.open(QIODevice::WriteOnly)) {
        return {};
    }
    if (file.write(bytes) != bytes.size()) {
        file.remove();
        return {};
    }

    {
        QMutexLocker locker(&mutex_);
        cachedFiles_.append(filePath);
    }
    return QUrl::fromLocalFile(filePath).toString();
}

void ResourcePreviewProvider::clear()
{
    QStringList files;
    {
        QMutexLocker locker(&mutex_);
        images_.clear();
        files = std::move(cachedFiles_);
        cachedFiles_.clear();
    }

    for (const QString& filePath : files) {
        QFile::remove(filePath);
    }
}

QImage ResourcePreviewProvider::requestImage(const QString& id, QSize* size, const QSize& requestedSize)
{
    QByteArray bytes;
    {
        QMutexLocker locker(&mutex_);
        bytes = images_.value(id);
    }

    QImage image;
    image.loadFromData(bytes);
    if (size != nullptr) {
        *size = image.size();
    }

    if (requestedSize.isValid() && !image.isNull()) {
        return image.scaled(requestedSize, Qt::KeepAspectRatio, Qt::SmoothTransformation);
    }
    return image;
}

QString ResourcePreviewProvider::cacheDirectory() const
{
    const QString base = QStandardPaths::writableLocation(QStandardPaths::CacheLocation);
    return QDir(base.isEmpty() ? QDir::tempPath() : base).filePath(QStringLiteral("resource-previews"));
}
