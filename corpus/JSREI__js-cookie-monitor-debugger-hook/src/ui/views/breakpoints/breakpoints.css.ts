/**
 * 断点列表视图样式
 */
export const breakpointsStyles = `
    /* 断点列表容器 */
    .jscookie-breakpoints-view {
        padding-bottom: 16px;
    }
    
    /* 空列表提示 */
    .jscookie-empty-list {
        background: #f8fafc;
        border-radius: 12px;
        padding: 32px 24px;
        text-align: center;
        margin: 24px 0;
        border: 1px dashed #cbd5e0;
    }
    
    .jscookie-empty-list p {
        color: #718096;
        font-size: 15px;
        margin: 0;
    }
    
    /* 断点列表 */
    .jscookie-breakpoint-list {
        margin-bottom: 24px;
    }
    
    .jscookie-breakpoint-items {
        display: flex;
        flex-direction: column;
        gap: 12px;
    }
    
    /* 断点项 */
    .jscookie-breakpoint-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px;
        background: #f8fafc;
        border-radius: 12px;
        border: 1px solid rgba(0, 0, 0, 0.05);
        transition: all 0.2s ease;
        position: relative;
        overflow: hidden;
    }
    
    .jscookie-breakpoint-item::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        height: 100%;
        width: 4px;
        background: linear-gradient(to bottom, #4f7dff, #6a8fff);
        border-radius: 2px 0 0 2px;
        opacity: 0.8;
    }
    
    .jscookie-breakpoint-item:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        transform: translateY(-2px);
        border-color: rgba(79, 125, 255, 0.2);
    }
    
    /* 断点内容 */
    .jscookie-breakpoint-content {
        flex: 1;
        padding: 0 16px;
        font-size: 14px;
        color: #4a5568;
        font-weight: 500;
        line-height: 1.5;
    }
    
    /* 断点操作按钮 */
    .jscookie-breakpoint-actions {
        display: flex;
        gap: 8px;
    }
    
    .jscookie-breakpoint-actions .jscookie-btn {
        padding: 6px 12px;
        font-size: 13px;
    }
    
    .jscookie-edit-rule-btn {
        color: #4f7dff !important;
        background-color: rgba(79, 125, 255, 0.1) !important;
        border: 1px solid rgba(79, 125, 255, 0.2) !important;
    }
    
    .jscookie-edit-rule-btn:hover {
        background-color: rgba(79, 125, 255, 0.15) !important;
    }
    
    .jscookie-delete-rule-btn {
        color: #e53e3e !important;
        background-color: rgba(229, 62, 62, 0.1) !important;
        border: 1px solid rgba(229, 62, 62, 0.2) !important;
    }
    
    .jscookie-delete-rule-btn:hover {
        background-color: rgba(229, 62, 62, 0.15) !important;
    }
    
    /* 添加规则按钮 */
    .jscookie-add-breakpoint-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        padding: 12px 16px;
        font-size: 15px;
        border-radius: 12px;
        transition: all 0.2s ease;
        position: relative;
        overflow: hidden;
    }
    
    .jscookie-add-breakpoint-btn::before {
        content: '+';
        margin-right: 8px;
        font-size: 18px;
        font-weight: 600;
    }
    
    .jscookie-add-breakpoint-btn:hover {
        transform: translateY(-2px);
    }
    
    /* 规则表单 */
    .jscookie-rule-form {
        background: #f8fafc;
        border-radius: 12px;
        padding: 20px;
        margin-top: 24px;
        border: 1px solid rgba(0, 0, 0, 0.05);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    }
    
    .jscookie-rule-form-title {
        font-size: 16px;
        font-weight: 600;
        color: #2d3748;
        margin: 0 0 16px 0;
        padding-bottom: 12px;
        border-bottom: 1px solid rgba(0, 0, 0, 0.05);
    }
    
    /* 表单操作按钮 */
    .jscookie-form-actions {
        display: flex;
        justify-content: flex-end;
        gap: 12px;
        margin-top: 24px;
    }
`;
