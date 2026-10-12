/**
 * 模态框样式
 */
export const modalStyles = `
    /* 模态框背景遮罩 */
    .jscookie-modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(135deg, rgba(79, 125, 255, 0.1), rgba(255, 107, 107, 0.1)),
                    rgba(0, 0, 0, 0.6);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
        animation: jscookie-fadeIn 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* 模态框容器 */
    .jscookie-modal {
        background: linear-gradient(145deg, #ffffff, #f8f9fa);
        border-radius: 16px;
        box-shadow:
            0 20px 40px rgba(0, 0, 0, 0.15),
            0 8px 16px rgba(0, 0, 0, 0.1),
            inset 0 1px 0 rgba(255, 255, 255, 0.8);
        width: 90%;
        max-width: 850px;
        max-height: 90vh;
        display: flex;
        flex-direction: column;
        overflow: hidden;
        position: relative;
        border: 1px solid rgba(255, 255, 255, 0.2);
        animation: jscookie-modalSlideIn 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    /* 模态框头部 */
    .jscookie-modal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 20px 24px;
        background: linear-gradient(to right, #4f7dff, #6a8fff);
        border-bottom: none;
        position: relative;
    }

    .jscookie-modal-title {
        font-size: 20px;
        font-weight: 600;
        color: white;
        margin: 0;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
        letter-spacing: 0.5px;
    }

    .jscookie-modal-close {
        background: rgba(255, 255, 255, 0.2);
        border: none;
        cursor: pointer;
        font-size: 18px;
        color: white;
        padding: 0;
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        transition: all 0.2s ease;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    .jscookie-modal-close:hover {
        background-color: rgba(255, 255, 255, 0.3);
        transform: scale(1.05);
    }
    
    /* 模态框内容区 */
    .jscookie-modal-content {
        flex: 1;
        overflow: auto;
        padding: 0;
        background-color: #ffffff;
        scrollbar-width: thin;
        scrollbar-color: #d1d5db #f3f4f6;
    }

    .jscookie-modal-content::-webkit-scrollbar {
        width: 8px;
    }

    .jscookie-modal-content::-webkit-scrollbar-track {
        background: #f3f4f6;
        border-radius: 4px;
    }

    .jscookie-modal-content::-webkit-scrollbar-thumb {
        background-color: #d1d5db;
        border-radius: 4px;
        border: 2px solid #f3f4f6;
    }

    /* 模态框底部 */
    .jscookie-modal-footer {
        display: flex;
        justify-content: flex-end;
        padding: 18px 24px;
        background: #f8f9fa;
        border-top: 1px solid rgba(0, 0, 0, 0.05);
        gap: 16px;
    }

    /* 按钮样式 */
    .jscookie-btn {
        padding: 10px 20px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        border: none;
        transition: all 0.2s ease;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        letter-spacing: 0.3px;
    }

    .jscookie-btn-primary {
        background: linear-gradient(to right, #4f7dff, #6a8fff);
        color: white;
    }

    .jscookie-btn-primary:hover {
        background: linear-gradient(to right, #3b6af8, #5a7fff);
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(79, 125, 255, 0.3);
    }

    .jscookie-btn-secondary {
        background-color: #f5f7fa;
        color: #4a5568;
        border: 1px solid rgba(0, 0, 0, 0.05);
    }

    .jscookie-btn-secondary:hover {
        background-color: #edf2f7;
        color: #2d3748;
        transform: translateY(-1px);
    }
    
    /* 响应式调整 */
    @media (max-width: 576px) {
        .jscookie-modal {
            width: 95%;
            max-height: 95vh;
        }

        .jscookie-modal-header,
        .jscookie-modal-footer {
            padding: 16px 20px;
        }

        .jscookie-btn {
            padding: 8px 16px;
        }
    }

    /* 动画定义 */
    @keyframes jscookie-fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    @keyframes jscookie-modalSlideIn {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    /* 表单元素美化 */
    .jscookie-form-row {
        margin-bottom: 16px;
    }

    .jscookie-form-row label {
        display: block;
        margin-bottom: 6px;
        font-weight: 500;
        color: #4a5568;
    }

    .jscookie-form-row input[type="text"],
    .jscookie-form-row input[type="number"],
    .jscookie-form-row select {
        width: 100%;
        padding: 10px 12px;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        background-color: #f8fafc;
        transition: all 0.2s ease;
        font-size: 14px;
    }

    .jscookie-form-row input[type="text"]:focus,
    .jscookie-form-row input[type="number"]:focus,
    .jscookie-form-row select:focus {
        border-color: #4f7dff;
        box-shadow: 0 0 0 3px rgba(79, 125, 255, 0.2);
        outline: none;
        background-color: #fff;
    }

    .jscookie-form-row.checkbox-row {
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .jscookie-form-row.checkbox-row input[type="checkbox"] {
        width: 18px;
        height: 18px;
        accent-color: #4f7dff;
    }

    .jscookie-form-row.checkbox-row label {
        margin-bottom: 0;
        cursor: pointer;
    }
`;