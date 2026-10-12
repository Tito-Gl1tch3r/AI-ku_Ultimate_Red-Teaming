#ifndef REARK_HEX_VIEWER_ITEM_H
#define REARK_HEX_VIEWER_ITEM_H

#include "model/HexDocumentModel.h"

#include <QMetaObject>
#include <QQuickPaintedItem>
#include <QQmlEngine>

class HexViewerItem : public QQuickPaintedItem {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(HexDocumentModel* model READ model WRITE setModel NOTIFY modelChanged)
    Q_PROPERTY(qreal scrollY READ scrollY WRITE setScrollY NOTIFY scrollYChanged)
    Q_PROPERTY(qreal documentWidth READ documentWidth NOTIFY documentMetricsChanged)
    Q_PROPERTY(qreal documentHeight READ documentHeight NOTIFY documentMetricsChanged)

public:
    explicit HexViewerItem(QQuickItem* parent = nullptr);

    [[nodiscard]] HexDocumentModel* model() const;
    void setModel(HexDocumentModel* model);
    [[nodiscard]] qreal scrollY() const;
    void setScrollY(qreal scrollY);
    [[nodiscard]] qreal documentWidth() const;
    [[nodiscard]] qreal documentHeight() const;

    void paint(QPainter* painter) override;

signals:
    void modelChanged();
    void scrollYChanged();
    void documentMetricsChanged();

private:
    void refreshMetrics();
    [[nodiscard]] int rowCount() const;

    HexDocumentModel* model_ = nullptr;
    QMetaObject::Connection modelConnection_;
    qreal scrollY_ = 0.0;
    qreal documentWidth_ = 0.0;
    qreal documentHeight_ = 0.0;
};

#endif // REARK_HEX_VIEWER_ITEM_H
