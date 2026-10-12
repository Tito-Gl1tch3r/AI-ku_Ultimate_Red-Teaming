import { modalStyles } from './modal.css';
import { createModalHTML } from './modal.html';
import { Tabs } from '../tabs';
import { tabsStyles } from '../tabs/tabs.css';
import { createBreakpointsView } from '../views/breakpoints';
import { createSettingsView } from '../views/settings';
import { createAboutView } from '../views/about';
import { breakpointsStyles } from '../views/breakpoints/breakpoints.css';
import { settingsStyles } from '../views/settings/settings.css';
import { aboutStyles } from '../views/about/about.css';
import logger from '../../logger/logger';

// 保存模态框实例
let modalInstance: HTMLElement | null = null;

/**
 * 注入模态框样式
 */
function injectStyles(): void {
    // 注入模态框基础样式
    if (!document.querySelector('#jscookie-modal-styles')) {
        const style = document.createElement('style');
        style.id = 'jscookie-modal-styles';
        style.textContent = modalStyles;
        document.head.appendChild(style);
    }

    // 注入断点列表样式
    if (!document.querySelector('#jscookie-breakpoints-styles')) {
        const breakpointsStyle = document.createElement('style');
        breakpointsStyle.id = 'jscookie-breakpoints-styles';
        breakpointsStyle.textContent = breakpointsStyles;
        document.head.appendChild(breakpointsStyle);
    }

    // 注入设置视图样式
    if (!document.querySelector('#jscookie-settings-styles')) {
        const settingsStyle = document.createElement('style');
        settingsStyle.id = 'jscookie-settings-styles';
        settingsStyle.textContent = settingsStyles;
        document.head.appendChild(settingsStyle);
    }

    // 注入关于页面样式
    if (!document.querySelector('#jscookie-about-styles')) {
        const aboutStyle = document.createElement('style');
        aboutStyle.id = 'jscookie-about-styles';
        aboutStyle.textContent = aboutStyles;
        document.head.appendChild(aboutStyle);
    }

    // 注入标签页样式
    if (!document.querySelector('#jscookie-tabs-styles')) {
        const tabsStyle = document.createElement('style');
        tabsStyle.id = 'jscookie-tabs-styles';
        tabsStyle.textContent = tabsStyles;
        document.head.appendChild(tabsStyle);
    }
}

/**
 * 创建模态框内容
 * @returns 模态框内容HTML
 */
function createModalContent(): string {
    // 创建各个标签页的内容
    const breakpointsContent = createBreakpointsView();
    const settingsContent = createSettingsView();
    const aboutContent = createAboutView();
    
    // 使用标签页组件创建内容
    const container = document.createElement('div');
    const tabs = new Tabs(container, [
        { id: 'jscookie-tab-breakpoints', title: '<i class="fas fa-bug"></i> 断点列表', content: breakpointsContent, active: true },
        { id: 'jscookie-tab-settings', title: '<i class="fas fa-cog"></i> 全局设置', content: settingsContent },
        { id: 'jscookie-tab-about', title: '<i class="fas fa-info-circle"></i> 关于', content: aboutContent }
    ]);
    
    // 获取生成的HTML
    return container.innerHTML || '';
}

/**
 * 绑定模态框事件
 * @param modal 模态框元素
 */
function bindModalEvents(modal: HTMLElement): void {
    // 关闭按钮
    const closeBtn = modal.querySelector('.jscookie-modal-close');
    if (closeBtn) {
        closeBtn.addEventListener('click', hideModal);
    }
    
    // 取消按钮
    const cancelBtn = modal.querySelector('.jscookie-cancel-btn');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', hideModal);
    }
    
    // 保存按钮
    const saveBtn = modal.querySelector('.jscookie-save-btn');
    if (saveBtn) {
        saveBtn.addEventListener('click', saveSettings);
    }
    
    // 点击遮罩关闭
    modal.addEventListener('click', (event) => {
        if (event.target === modal) {
            hideModal();
        }
    });
    
    // ESC按键关闭
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && isModalVisible()) {
            hideModal();
        }
    });

    // 绑定断点相关事件
    bindBreakpointEvents(modal);
}

/**
 * 绑定断点相关事件
 * @param modal 模态框元素
 */
function bindBreakpointEvents(modal: HTMLElement): void {
    // 添加新规则按钮
    const addBtn = modal.querySelector('.jscookie-add-breakpoint-btn');
    if (addBtn) {
        addBtn.addEventListener('click', () => {
            showAddRuleForm();
        });
    }

    // 编辑规则按钮
    const editBtns = modal.querySelectorAll('.jscookie-edit-rule-btn');
    editBtns.forEach(btn => {
        btn.addEventListener('click', (event) => {
            const target = event.target as HTMLElement;
            const index = target.getAttribute('data-index');
            if (index !== null) {
                editRule(parseInt(index));
            }
        });
    });

    // 删除规则按钮
    const deleteBtns = modal.querySelectorAll('.jscookie-delete-rule-btn');
    deleteBtns.forEach(btn => {
        btn.addEventListener('click', (event) => {
            const target = event.target as HTMLElement;
            const index = target.getAttribute('data-index');
            if (index !== null) {
                deleteRule(parseInt(index));
            }
        });
    });
}

/**
 * 保存配置
 */
function saveSettings(): void {
    try {
        // 遍历表单并收集数据
        const form = document.querySelector('.jscookie-settings-form');
        if (form) {
            // 收集表单数据的逻辑...
            
            logger.info('设置已保存');
            hideModal();
        }
    } catch (error) {
        logger.error('保存设置失败', error);
    }
}

/**
 * 显示模态框
 */
export function showModal(): void {
    // 防止重复创建
    if (isModalVisible()) {
        return;
    }
    
    try {
        // 注入样式
        injectStyles();
        
        // 创建模态框内容
        const content = createModalContent();
        
        // 创建模态框
        const modalHTML = createModalHTML('JS Cookie Monitor 配置', content);

        // 使用 DOMParser 来避免 TrustedHTML 错误
        const parser = new DOMParser();
        const doc = parser.parseFromString(modalHTML.trim(), 'text/html');
        modalInstance = doc.body.firstChild as HTMLElement;
        
        // 添加到文档
        document.body.appendChild(modalInstance);
        
        // 防止body滚动
        document.body.style.overflow = 'hidden';
        
        // 绑定事件
        bindModalEvents(modalInstance);
        
        // 初始化标签页
        initTabs();
    } catch (error) {
        logger.error('显示模态框失败', error);
    }
}

/**
 * 初始化标签页
 */
function initTabs(): void {
    try {
        // 查找模态框内容容器
        const content = document.querySelector('.jscookie-modal-content');
        if (content && content instanceof HTMLElement) {
            // 创建标签页
            new Tabs(content, [
                { id: 'jscookie-tab-breakpoints', title: '<i class="fas fa-bug"></i> 断点列表', content: createBreakpointsView(), active: true },
                { id: 'jscookie-tab-settings', title: '<i class="fas fa-cog"></i> 全局设置', content: createSettingsView() },
                { id: 'jscookie-tab-about', title: '<i class="fas fa-info-circle"></i> 关于', content: createAboutView() }
            ]);
        }
    } catch (error) {
        logger.error('初始化标签页失败', error);
    }
}

/**
 * 隐藏模态框
 */
export function hideModal(): void {
    if (modalInstance) {
        // 恢复body滚动
        document.body.style.overflow = '';
        
        // 移除模态框
        modalInstance.remove();
        modalInstance = null;
    }
}

/**
 * 检查模态框是否可见
 */
export function isModalVisible(): boolean {
    return !!modalInstance && document.body.contains(modalInstance);
}

/**
 * 显示添加规则表单
 */
function showAddRuleForm(): void {
    try {
        logger.info('显示添加规则表单');

        // 创建规则表单HTML
        const formHTML = createRuleFormHTML();

        // 查找断点表单容器
        const formContainer = document.querySelector('.jscookie-breakpoint-form');
        if (formContainer) {
            // 使用 DOMParser 来避免 TrustedHTML 错误
            const parser = new DOMParser();
            const doc = parser.parseFromString(formHTML, 'text/html');
            const formElement = doc.body.firstChild as HTMLElement;

            // 替换现有内容
            formContainer.innerHTML = '';
            formContainer.appendChild(formElement);

            // 绑定表单事件
            bindRuleFormEvents(formContainer);
        }
    } catch (error) {
        logger.error('显示添加规则表单失败', error);
    }
}

/**
 * 编辑规则
 * @param index 规则索引
 */
function editRule(index: number): void {
    logger.info(`编辑规则 ${index}`);
    // TODO: 实现编辑规则功能
}

/**
 * 删除规则
 * @param index 规则索引
 */
function deleteRule(index: number): void {
    logger.info(`删除规则 ${index}`);
    // TODO: 实现删除规则功能
}

/**
 * 创建规则表单HTML
 */
function createRuleFormHTML(): string {
    return `
        <div class="jscookie-rule-form">
            <h4 class="jscookie-rule-form-title">添加新的断点规则</h4>

            <div class="jscookie-form-row">
                <label for="rule-type">规则类型</label>
                <select id="rule-type" name="ruleType">
                    <option value="string">字符串匹配</option>
                    <option value="regex">正则表达式</option>
                    <option value="object">高级规则</option>
                </select>
            </div>

            <div class="jscookie-form-row">
                <label for="rule-value">规则值</label>
                <input type="text" id="rule-value" name="ruleValue" placeholder="请输入规则值" />
            </div>

            <div class="jscookie-form-actions">
                <button type="button" class="jscookie-btn jscookie-btn-secondary jscookie-cancel-rule-btn">取消</button>
                <button type="button" class="jscookie-btn jscookie-btn-primary jscookie-save-rule-btn">保存</button>
            </div>
        </div>
    `;
}

/**
 * 绑定规则表单事件
 * @param container 表单容器
 */
function bindRuleFormEvents(container: Element): void {
    // 取消按钮
    const cancelBtn = container.querySelector('.jscookie-cancel-rule-btn');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
            hideRuleForm();
        });
    }

    // 保存按钮
    const saveBtn = container.querySelector('.jscookie-save-rule-btn');
    if (saveBtn) {
        saveBtn.addEventListener('click', () => {
            saveRule();
        });
    }
}

/**
 * 隐藏规则表单
 */
function hideRuleForm(): void {
    const formContainer = document.querySelector('.jscookie-breakpoint-form');
    if (formContainer) {
        formContainer.innerHTML = `
            <div class="jscookie-form-row">
                <button class="jscookie-btn jscookie-btn-primary jscookie-add-breakpoint-btn">
                    添加新规则
                </button>
            </div>
        `;

        // 重新绑定添加按钮事件
        const addBtn = formContainer.querySelector('.jscookie-add-breakpoint-btn');
        if (addBtn) {
            addBtn.addEventListener('click', () => {
                showAddRuleForm();
            });
        }
    }
}

/**
 * 保存规则
 */
function saveRule(): void {
    try {
        const ruleTypeSelect = document.querySelector('#rule-type') as HTMLSelectElement;
        const ruleValueInput = document.querySelector('#rule-value') as HTMLInputElement;

        if (!ruleTypeSelect || !ruleValueInput) {
            logger.error('找不到表单元素');
            return;
        }

        const ruleType = ruleTypeSelect.value;
        const ruleValue = ruleValueInput.value.trim();

        if (!ruleValue) {
            alert('请输入规则值');
            return;
        }

        logger.info(`保存规则: 类型=${ruleType}, 值=${ruleValue}`);

        // TODO: 实现保存规则到配置的功能

        // 暂时显示成功消息
        alert('规则保存成功！（注意：当前为演示版本，规则不会真正保存）');

        // 隐藏表单
        hideRuleForm();

    } catch (error) {
        logger.error('保存规则失败', error);
        alert('保存规则失败，请查看控制台错误信息');
    }
}