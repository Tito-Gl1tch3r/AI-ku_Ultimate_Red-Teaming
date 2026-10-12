from flask import Flask, request, jsonify, render_template_string, redirect, url_for
from flask_cors import CORS
import os
import json
import time
from datetime import datetime
from osint_assistant import OSINTAssistant

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# HTML template for the application
APP_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OSINT Assistant</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            /* Light Mode Colors */
            --primary-color: #3b82f6;  /* Blue */
            --primary-hover: #2563eb;
            --primary-light: rgba(59, 130, 246, 0.1);
            --primary-dark: #1d4ed8;
            
            /* Dark Mode Accent (Red) */
            --accent-color: #3b82f6;  /* Changed to blue for consistency */
            --accent-hover: #2563eb;
            --accent-light: rgba(59, 130, 246, 0.1);
            --accent-dark: #1d4ed8;
            
            /* Alert Colors */
            --success-color: #10b981;
            --warning-color: #f59e0b;
            --danger-color: #ef4444;
            
            /* Light Mode */
            --card-bg-light: #ffffff;
            --card-border-light: #e5e7eb;
            --text-primary-light: #111827;
            --text-secondary-light: #4b5563;
            --bg-light: #f8fafc;
            
            /* Dark Mode */
            --card-bg-dark: #1e1e1e;  /* Slightly lighter than background for contrast */
            --card-border-dark: #333333;
            --text-primary-dark: #ffffff;
            --text-secondary-dark: #d1d5db;
            --bg-dark: #121212;  /* Dark background */
            
            /* Badges Light Mode */
            --badge-bg-blue-light: #e6f2ff;
            --badge-text-blue-light: #1976d2;
            --badge-bg-green-light: #e6ffed;
            --badge-text-green-light: #10b981;
            --badge-bg-yellow-light: #fffbeb;
            --badge-text-yellow-light: #f59e0b;
            --badge-bg-red-light: #fee2e2;
            --badge-text-red-light: #ef4444;
            --badge-bg-gray-light: #f3f4f6;
            --badge-text-gray-light: #6b7280;
            
            /* Badges Dark Mode */
            --badge-bg-blue-dark: rgba(59, 130, 246, 0.2);
            --badge-text-blue-dark: #60a5fa;
            --badge-bg-green-dark: rgba(16, 185, 129, 0.2);
            --badge-text-green-dark: #34d399;
            --badge-bg-yellow-dark: rgba(245, 158, 11, 0.2);
            --badge-text-yellow-dark: #fbbf24;
            --badge-bg-red-dark: rgba(239, 68, 68, 0.2);
            --badge-text-red-dark: #f87171;
            --badge-bg-gray-dark: rgba(107, 114, 128, 0.2);
            --badge-text-gray-dark: #d1d5db;
        }
        
        * {
            font-family: 'Inter', sans-serif;
            transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease;
        }
        
        /* Dark mode classes */
        .dark {
            color-scheme: dark;
        }
        
        .dark body {
            background-color: var(--bg-dark);
            color: var(--text-primary-dark);
        }
        
        body.dark {
            background-color: var(--bg-dark);
            color: var(--text-primary-dark);
        }
        
        .light body {
            background-color: var(--bg-light);
            color: var(--text-primary-light);
        }
        
        body.light {
            background-color: var(--bg-light);
            color: var(--text-primary-light);
        }

        .loading {
            display: inline-block;
            width: 50px;
            height: 50px;
            border: 3px solid rgba(59, 130, 246, 0.3);
            border-radius: 50%;
            border-top-color: #3b82f6;
            animation: spin 1s ease-in-out infinite;
        }
        
        .dark .loading {
            border: 3px solid rgba(220, 38, 38, 0.3);
            border-top-color: #dc2626;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .line-clamp-2 {
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;  
            overflow: hidden;
        }
        
        .card {
            transition: all 0.2s ease;
        }
        
        .light .card {
            background-color: var(--card-bg-light);
            border: 1px solid var(--card-border-light);
        }
        
        .dark .card {
            background-color: var(--card-bg-dark);
            border: 1px solid var(--card-border-dark);
            color: var(--text-primary-dark);
        }
        
        .card:hover {
            transform: translateY(-3px);
        }
        
        .light .card:hover {
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        }
        
        .dark .card:hover {
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.4);
        }
        
        .result-item {
            border-left: 3px solid transparent;
            transition: all 0.2s ease;
        }
        
        .light .result-item:hover {
            border-left-color: var(--primary-color);
            background-color: rgba(59, 130, 246, 0.05);
        }
        
        .dark .result-item:hover {
            border-left-color: var(--accent-color);
            background-color: rgba(59, 130, 246, 0.1);
        }
        
        .light .selected-result {
            border-left-color: var(--primary-color);
            background-color: rgba(59, 130, 246, 0.1);
        }
        
        .dark .selected-result {
            border-left-color: var(--accent-color);
            background-color: rgba(59, 130, 246, 0.15);
        }
        
        .badge {
            font-size: 0.75rem;
            padding: 0.25rem 0.5rem;
            border-radius: 9999px;
            font-weight: 500;
            display: inline-flex;
            align-items: center;
        }
        
        .light .badge-blue {
            background-color: var(--badge-bg-blue-light);
            color: var(--badge-text-blue-light);
        }
        
        .dark .badge-blue {
            background-color: rgba(59, 130, 246, 0.3);
            color: #93c5fd;
        }
        
        .light .badge-green {
            background-color: var(--badge-bg-green-light);
            color: var(--badge-text-green-light);
        }
        
        .dark .badge-green {
            background-color: var(--badge-bg-green-dark);
            color: var(--badge-text-green-dark);
        }
        
        .light .badge-yellow {
            background-color: var(--badge-bg-yellow-light);
            color: var(--badge-text-yellow-light);
        }
        
        .dark .badge-yellow {
            background-color: var(--badge-bg-yellow-dark);
            color: var(--badge-text-yellow-dark);
        }
        
        .light .badge-red {
            background-color: var(--badge-bg-red-light);
            color: var(--badge-text-red-light);
        }
        
        .dark .badge-red {
            background-color: var(--badge-bg-red-dark);
            color: var(--badge-text-red-dark);
        }
        
        .light .badge-gray {
            background-color: var(--badge-bg-gray-light);
            color: var(--badge-text-gray-light);
        }
        
        .dark .badge-gray {
            background-color: var(--badge-bg-gray-dark);
            color: var(--badge-text-gray-dark);
        }
        
        /* Theme toggle switch */
        .theme-switch {
            position: relative;
            display: inline-block;
            width: 60px;
            height: 30px;
        }
        
        .theme-switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }
        
        .slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #3b82f6;  /* Blue for light mode (default) */
            transition: 0.4s;
            border-radius: 30px;
        }
        
        .slider:before {
            position: absolute;
            content: "";
            height: 22px;
            width: 22px;
            left: 4px;
            bottom: 4px;
            background-color: white;
            transition: 0.4s;
            border-radius: 50%;
        }
        
        input:checked + .slider {
            background-color: #3b82f6;  /* Blue for dark mode too for consistency */
        }
        
        input:focus + .slider {
            box-shadow: 0 0 1px #3b82f6;
        }
        
        input:checked + .slider:before {
            transform: translateX(30px);
        }
        
        /* Modal styles */
        .modal {
            display: none;
            position: fixed;
            z-index: 50;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            overflow: auto;
            background-color: rgba(0, 0, 0, 0.5);
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        
        .modal-content {
            position: relative;
            margin: 10% auto;
            width: 90%;
            max-width: 600px;
            transform: translateY(-20px);
            transition: transform 0.3s ease;
        }
        
        .modal.show {
            display: block;
            opacity: 1;
        }
        
        .modal.show .modal-content {
            transform: translateY(0);
        }
        
        /* Information panels for dark mode */
        .light .info-panel {
            background-color: #f9fafb;
            border: 1px solid #e5e7eb;
        }
        
        .dark .info-panel {
            background-color: #1e1e1e;
            border: 1px solid #333333;
        }
        
        /* Button styles for dark mode */
        .light .btn-primary {
            background-color: var(--primary-color);
            color: white;
        }
        
        .light .btn-primary:hover {
            background-color: var(--primary-hover);
        }
        
        .dark .btn-primary {
            background-color: var(--accent-color);
            color: white;
        }
        
        .dark .btn-primary:hover {
            background-color: var(--accent-hover);
        }
        
        /* Custom scrollbar for dark mode */
        .dark ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        .dark ::-webkit-scrollbar-track {
            background: #1a1a1a;
        }
        
        .dark ::-webkit-scrollbar-thumb {
            background: #333333;
            border-radius: 4px;
        }
        
        .dark ::-webkit-scrollbar-thumb:hover {
            background: #444444;
        }

        /* Page background */
        .dark main {
            background-color: var(--bg-dark);
        }

        .light main {
            background-color: var(--bg-light);
        }

        /* Search button */
        .dark .search-btn {
            background-color: var(--accent-color);
            color: white;
        }

        .dark .search-btn:hover {
            background-color: var(--accent-hover);
        }

        .light .search-btn {
            background-color: var(--primary-color);
            color: white;
        }

        .light .search-btn:hover {
            background-color: var(--primary-hover);
        }

        /* Advanced panel */
        .dark .advanced-panel {
            background-color: #1e1e1e;
            border-color: #333333;
        }

        .light .advanced-panel {
            background-color: #f9fafb;
            border-color: #e5e7eb;
        }

        /* Footer links */
        .dark .footer-link {
            color: var(--text-secondary-dark);
        }
        
        .dark .footer-link:hover {
            color: var(--accent-color);
        }

        .light .footer-link {
            color: var(--text-secondary-light);
        }
        
        .light .footer-link:hover {
            color: var(--primary-color);
        }

        /* Reset all default browser styles for consistent appearance */
        button, input, select, textarea {
            font-family: inherit;
            font-size: 100%;
            line-height: 1.15;
            margin: 0;
        }

        button {
            cursor: pointer;
        }

        .dark input, .dark textarea, .dark select {
            background-color: #333;
            color: var(--text-primary-dark);
            border-color: var(--card-border-dark);
        }
        
        .dark input:focus, .dark textarea:focus, .dark select:focus {
            border-color: var(--accent-color);
            box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.3);
        }

        /* Card styles for dark mode consistency */
        .dark .card {
            background-color: var(--card-bg-dark);
            border-color: var(--card-border-dark);
            color: var(--text-primary-dark);
        }

        /* Table styles dark mode */
        .dark thead {
            background-color: #1a1a1a;
        }

        .dark tbody {
            background-color: var(--card-bg-dark);
        }

        /* Input placeholder color for dark mode */
        .dark input::placeholder {
            color: var(--text-secondary-dark);
            opacity: 0.7;
        }

        /* Text colors for dark mode */
        .dark .text-gray-600, 
        .dark .text-gray-700,
        .dark .text-gray-800 {
            color: var(--text-secondary-dark);
        }
        
        .dark .text-gray-300,
        .dark .text-gray-400 {
            color: #bfbfbf;
        }

        /* Make label text more visible in dark mode */
        .dark .info-panel .text-gray-600 {
            color: #a8b1cf !important;
        }

        /* Make content text more visible in dark mode */
        .dark .info-panel .text-gray-800,
        .dark .info-panel .text-gray-900 {
            color: #ffffff !important;
        }

        /* Improve readability for key-value pairs */
        .dark .info-panel .justify-between span:first-child {
            color: #a8b1cf !important;
        }
        
        .dark .info-panel .justify-between span:last-child {
            color: #ffffff !important;
        }

        /* Content Summary specific styling */
        .dark .info-panel p.text-gray-800,
        .dark .info-panel p.text-gray-300,
        .dark .info-panel p.leading-relaxed {
            color: #e2e8f0 !important;
            line-height: 1.6;
        }
        
        /* Improve table text visibility */
        .dark table th {
            color: #d1d5db !important;
        }
        
        .dark table td {
            color: #f3f4f6 !important;
        }

        /* Badge style updates for dark mode */
        .dark .badge-blue {
            background-color: rgba(59, 130, 246, 0.3);
            color: #93c5fd;
        }
        
        /* Entity section in dark mode */
        .dark .flex-wrap .badge {
            background-color: rgba(59, 130, 246, 0.3);
            color: #93c5fd;
            border: 1px solid rgba(59, 130, 246, 0.5);
        }
        
        /* Icons in dark mode */
        .dark .ri-information-line,
        .dark .ri-price-tag-3-line,
        .dark .ri-text,
        .dark .ri-mind-map,
        .dark .text-blue-500 {
            color: #60a5fa !important;
        }
    </style>
</head>
<body class="min-h-screen flex flex-col dark">
    <header class="bg-gradient-to-r from-black to-red-900 text-white shadow-lg">
        <div class="container mx-auto p-6">
            <div class="flex flex-col md:flex-row md:items-center md:justify-between">
                <div>
                    <div class="flex items-center">
                        <i class="ri-spy-fill text-2xl mr-3 text-red-400"></i>
                        <h1 class="text-3xl font-bold">OSINT Assistant</h1>
                    </div>
                    <p class="text-red-200 mt-1">AI-Enhanced Open Source Intelligence Tool</p>
                </div>
                <div class="mt-4 md:mt-0 flex items-center">
                    <div class="flex items-center text-sm text-red-200 mr-6">
                        <i class="ri-shield-keyhole-line mr-2"></i>
                        <span>Secure Intelligence</span>
                    </div>
                    <div class="flex items-center">
                        <i class="ri-sun-line text-yellow-400 mr-2"></i>
                        <label class="theme-switch">
                            <input type="checkbox" id="themeToggle" checked>
                            <span class="slider"></span>
                        </label>
                        <i class="ri-moon-line text-gray-300 ml-2"></i>
                    </div>
                </div>
            </div>
        </div>
    </header>
    
    <main class="container mx-auto p-4 md:p-6 flex-grow bg-gray-50 dark:bg-[#121212]">
        <div class="card rounded-xl shadow-md p-6 mb-8">
            <form id="searchForm" action="/search" method="post">
                <h2 class="text-xl font-semibold mb-4 dark:text-white">
                    <i class="ri-search-eye-line mr-2 text-red-500"></i>
                    Begin Your Intelligence Search
                </h2>
                <div class="mb-5">
                    <label for="query" class="block text-sm font-medium mb-1 dark:text-gray-300">
                        Search Query
                    </label>
                    <div class="relative">
                        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <i class="ri-search-line text-gray-400 dark:text-gray-500"></i>
                        </div>
                        <input 
                            id="query" 
                            name="query"
                            type="text" 
                            placeholder="Enter your OSINT search query (e.g., 'cybersecurity threats 2023')" 
                            class="w-full pl-10 pr-4 py-3 border border-gray-300 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-red-500 focus:border-blue-500 dark:focus:border-red-500 transition-all bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
                            required
                            value="{{ query if query else '' }}"
                        >
                    </div>
                </div>
                
                <div class="flex items-center mb-4">
                    <button 
                        type="button" 
                        id="advancedToggle"
                        class="text-sm text-blue-600 dark:text-red-400 hover:text-blue-800 dark:hover:text-red-300 flex items-center focus:outline-none"
                    >
                        <svg 
                            id="toggleIcon"
                            class="h-4 w-4 mr-1 transition-transform transform" 
                            fill="none" 
                            viewBox="0 0 24 24" 
                            stroke="currentColor"
                        >
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                        </svg>
                        Advanced Options
                    </button>
                </div>
                
                <div id="advancedOptions" class="mb-5 p-5 rounded-lg hidden border advanced-panel">
                    <div class="mb-4">
                        <label for="apiKey" class="block text-sm font-medium mb-1 dark:text-gray-300">
                            <i class="ri-key-2-line mr-1 text-blue-500 dark:text-red-500"></i>
                            Perplexity API Key (Optional)
                        </label>
                        <input 
                            id="apiKey"
                            name="api_key" 
                            type="password" 
                            placeholder="Enter your API key" 
                            class="w-full px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-red-500 focus:border-blue-500 dark:focus:border-red-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
                        >
                        <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                            Leave empty to use the API key from the .env file
                        </p>
                    </div>
                    
                    <div>
                        <label for="numResults" class="block text-sm font-medium mb-1 dark:text-gray-300">
                            <i class="ri-list-ordered mr-1 text-blue-500 dark:text-red-500"></i>
                            Number of Results
                        </label>
                        <div class="flex items-center">
                            <input 
                                id="numResults"
                                name="num_results" 
                                type="number" 
                                value="10" 
                                min="1" 
                                max="50" 
                                class="w-full px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-red-500 focus:border-blue-500 dark:focus:border-red-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
                            >
                            <div class="ml-2 text-sm text-gray-500 dark:text-gray-400">
                                (1-50)
                            </div>
                        </div>
                    </div>
                </div>
                
                <div>
                    <button 
                        type="submit" 
                        class="w-full search-btn py-3 px-6 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-red-500 focus:ring-offset-2 transition-colors flex justify-center items-center font-medium"
                    >
                        <i class="ri-search-2-line mr-2"></i>
                        Search
                    </button>
                </div>
            </form>
        </div>
        
        <!-- Loading indicator -->
        {% if is_loading %}
        <div class="flex flex-col items-center justify-center mt-12" id="loading">
            <div class="loading mb-4"></div>
            <p class="text-blue-600 dark:text-red-400 font-medium">Gathering intelligence data...</p>
        </div>
        {% endif %}
        
        <!-- Error message -->
        {% if error %}
        <div class="mt-6 p-4 bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 rounded-r-lg text-red-700 dark:text-red-400">
            <div class="flex">
                <div class="flex-shrink-0">
                    <i class="ri-error-warning-line text-red-500"></i>
                </div>
                <div class="ml-3">
                    <p class="font-medium">Error Occurred</p>
                    <p class="mt-1">{{ error }}</p>
                </div>
            </div>
        </div>
        {% endif %}
        
        <!-- Results -->
        {% if results %}
        <div class="mt-8 grid grid-cols-1 lg:grid-cols-3 gap-6">
            <!-- Search Results List -->
            <div class="lg:col-span-1">
                <div class="card rounded-xl shadow-md p-4 sticky top-4">
                    <div class="flex items-center mb-4">
                        <i class="ri-list-check mr-2 text-blue-500 dark:text-red-500"></i>
                        <h2 class="text-xl font-semibold dark:text-white">Search Results</h2>
                    </div>
                    <div class="overflow-y-auto max-h-[calc(100vh-240px)]">
                        <ul class="divide-y divide-gray-200 dark:divide-gray-800">
                            {% for result in results.collected_data %}
                            <li 
                                class="py-4 px-3 cursor-pointer transition rounded-lg result-item {% if selected_url == result.url %}selected-result{% endif %}"
                                onclick="window.location.href='{{ url_for('search_results', session_id=session_id, result_index=loop.index0) }}'"
                            >
                                <h3 class="text-base font-medium text-blue-600 dark:text-red-400 mb-1">{{ result.title }}</h3>
                                <p class="text-sm text-gray-600 dark:text-gray-400 mb-1 truncate flex items-center">
                                    <i class="ri-link text-gray-400 mr-1 text-xs"></i>
                                    {{ result.url }}
                                </p>
                                <p class="text-sm text-gray-800 dark:text-gray-300 line-clamp-2">{{ result.snippet }}</p>
                                <div class="mt-2 flex justify-between text-xs">
                                    <span class="badge badge-blue">
                                        {{ result.source_type }}
                                    </span>
                                    <span class="text-gray-500 dark:text-gray-400 flex items-center">
                                        <i class="ri-time-line mr-1"></i>
                                        {{ result.timestamp }}
                                    </span>
                                </div>
                            </li>
                            {% endfor %}
                        </ul>
                    </div>
                </div>
            </div>
            
            <!-- Analysis View -->
            <div class="lg:col-span-2">
                {% if selected_result and selected_analysis %}
                <div class="card rounded-xl shadow-md overflow-hidden">
                    <div class="bg-gradient-to-r from-blue-50 to-blue-100 dark:from-red-900/30 dark:to-black p-5 border-b border-blue-200 dark:border-red-900">
                        <div class="flex justify-between items-start">
                            <div>
                                <h2 class="text-xl font-semibold text-gray-800 dark:text-white">{{ selected_result.title }}</h2>
                                <a 
                                    href="{{ selected_result.url }}" 
                                    target="_blank" 
                                    rel="noopener noreferrer"
                                    class="text-blue-600 dark:text-red-400 hover:text-blue-800 dark:hover:text-red-300 text-sm mt-1 block flex items-center"
                                >
                                    <i class="ri-external-link-line mr-1 text-xs"></i>
                                    {{ selected_result.url }}
                                </a>
                            </div>
                            <div>
                                <a 
                                    href="{{ selected_result.url }}" 
                                    target="_blank" 
                                    rel="noopener noreferrer"
                                    class="inline-flex items-center px-3 py-1 border border-blue-300 dark:border-red-800 text-sm font-medium rounded-md text-blue-700 dark:text-red-400 bg-blue-50 dark:bg-black hover:bg-blue-100 dark:hover:bg-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-red-500"
                                >
                                    <i class="ri-external-link-line mr-1"></i>
                                    Visit Source
                                </a>
                            </div>
                        </div>
                    </div>
                    
                    <div class="p-6">
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                            <div class="info-panel p-5 rounded-lg">
                                <div class="flex items-center mb-3">
                                    <i class="ri-information-line text-blue-500 dark:text-red-500 mr-2"></i>
                                    <h3 class="text-lg font-medium dark:text-white">Source Details</h3>
                                </div>
                                <div class="space-y-3">
                                    <div class="flex items-center justify-between">
                                        <span class="text-sm text-gray-600 dark:text-gray-400 flex items-center">
                                            <i class="ri-global-line text-gray-400 mr-1"></i>
                                            Domain:
                                        </span>
                                        <span class="text-sm font-medium text-gray-800 dark:text-gray-200">{{ selected_analysis.domain }}</span>
                                    </div>
                                    <div class="flex items-center justify-between">
                                        <span class="text-sm text-gray-600 dark:text-gray-400 flex items-center">
                                            <i class="ri-shield-check-line text-gray-400 mr-1"></i>
                                            Credibility:
                                        </span>
                                        <span class="badge 
                                            {% if selected_analysis.credibility_score >= 0.7 %}
                                                badge-green
                                            {% elif selected_analysis.credibility_score >= 0.4 %}
                                                badge-yellow
                                            {% else %}
                                                badge-red
                                            {% endif %}
                                        ">
                                            {{ (selected_analysis.credibility_score * 100) | int }}% 
                                            {% if selected_analysis.credibility_score >= 0.7 %}
                                                <i class="ri-check-line ml-1"></i>
                                            {% elif selected_analysis.credibility_score >= 0.4 %}
                                                <i class="ri-alert-line ml-1"></i>
                                            {% else %}
                                                <i class="ri-close-circle-line ml-1"></i>
                                            {% endif %}
                                        </span>
                                    </div>
                                    <div class="flex items-center justify-between">
                                        <span class="text-sm text-gray-600 dark:text-gray-400 flex items-center">
                                            <i class="ri-message-2-line text-gray-400 mr-1"></i>
                                            Sentiment:
                                        </span>
                                        <span class="badge 
                                            {% if selected_analysis.sentiment == 'positive' %}
                                                badge-green
                                            {% elif selected_analysis.sentiment == 'negative' %}
                                                badge-red
                                            {% else %}
                                                badge-gray
                                            {% endif %}
                                        ">
                                            {{ selected_analysis.sentiment | capitalize }}
                                            {% if selected_analysis.sentiment == 'positive' %}
                                                <i class="ri-emotion-happy-line ml-1"></i>
                                            {% elif selected_analysis.sentiment == 'negative' %}
                                                <i class="ri-emotion-unhappy-line ml-1"></i>
                                            {% else %}
                                                <i class="ri-emotion-normal-line ml-1"></i>
                                            {% endif %}
                                        </span>
                                    </div>
                                    <div class="flex items-center justify-between">
                                        <span class="text-sm text-gray-600 dark:text-gray-400 flex items-center">
                                            <i class="ri-calendar-line text-gray-400 mr-1"></i>
                                            Published:
                                        </span>
                                        <span class="text-sm text-gray-800 dark:text-gray-200">{{ selected_analysis.timestamps.published }}</span>
                                    </div>
                                    <div class="flex items-center justify-between">
                                        <span class="text-sm text-gray-600 dark:text-gray-400 flex items-center">
                                            <i class="ri-time-line text-gray-400 mr-1"></i>
                                            Last Updated:
                                        </span>
                                        <span class="text-sm text-gray-800 dark:text-gray-200">{{ selected_analysis.timestamps.last_updated }}</span>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="info-panel p-5 rounded-lg">
                                <div class="flex items-center mb-3">
                                    <i class="ri-price-tag-3-line text-blue-500 dark:text-red-500 mr-2"></i>
                                    <h3 class="text-lg font-medium dark:text-white">Key Entities</h3>
                                </div>
                                <div class="flex flex-wrap gap-2">
                                    {% for entity in selected_analysis.key_entities %}
                                    <span class="badge badge-blue">
                                        {{ entity }}
                                    </span>
                                    {% endfor %}
                                </div>
                            </div>
                        </div>
                        
                        <div class="info-panel p-5 rounded-lg mt-6">
                            <div class="flex items-center mb-3">
                                <i class="ri-text text-blue-500 dark:text-red-500 mr-2"></i>
                                <h3 class="text-lg font-medium dark:text-white">Content Summary</h3>
                            </div>
                            <p class="text-gray-800 dark:text-gray-300 leading-relaxed">{{ selected_result.snippet }}</p>
                        </div>
                        
                        {% if selected_analysis.connections and selected_analysis.connections|length > 0 %}
                        <div class="info-panel p-5 rounded-lg mt-6">
                            <div class="flex items-center mb-3">
                                <i class="ri-mind-map text-blue-500 dark:text-red-500 mr-2"></i>
                                <h3 class="text-lg font-medium dark:text-white">Entity Connections</h3>
                            </div>
                            <div class="overflow-x-auto">
                                <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-800 border border-gray-200 dark:border-gray-800 rounded-lg overflow-hidden">
                                    <thead class="bg-blue-50 dark:bg-black">
                                        <tr>
                                            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wider">From</th>
                                            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wider">Relationship</th>
                                            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wider">To</th>
                                        </tr>
                                    </thead>
                                    <tbody class="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-800">
                                        {% for connection in selected_analysis.connections %}
                                        <tr>
                                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">{{ connection.from }}</td>
                                            <td class="px-6 py-4 whitespace-nowrap text-sm text-blue-600 dark:text-red-400 font-medium">{{ connection.relationship }}</td>
                                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">{{ connection.to }}</td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        {% endif %}
                    </div>
                </div>
                {% else %}
                <div class="card rounded-xl shadow-md p-8 h-full flex flex-col items-center justify-center text-center">
                    <div class="w-24 h-24 rounded-full bg-blue-100 dark:bg-red-900/30 flex items-center justify-center mb-6">
                        <i class="ri-search-eye-line text-blue-600 dark:text-red-500 text-4xl"></i>
                    </div>
                    <h3 class="text-xl font-semibold text-gray-800 dark:text-white mb-2">
                        {% if results %}
                            Select a result to view analysis
                        {% else %}
                            Start your intelligence search
                        {% endif %}
                    </h3>
                    <p class="text-gray-500 dark:text-gray-400 max-w-md">
                        {% if results %}
                            Click on any search result from the list to view detailed analysis and insights.
                        {% else %}
                            Enter your search query above to begin gathering open-source intelligence data.
                        {% endif %}
                    </p>
                </div>
                {% endif %}
            </div>
        </div>
        {% endif %}
    </main>
    
    <footer class="bg-black text-white py-6 mt-12">
        <div class="container mx-auto px-6">
            <div class="flex flex-col md:flex-row justify-between items-center">
                <div class="flex items-center mb-4 md:mb-0">
                    <i class="ri-spy-fill text-xl mr-2 text-red-500"></i>
                    <p class="font-medium">OSINT Assistant &copy; {{ current_year }}</p>
                </div>
                <div class="flex space-x-6">
                    <a href="#" class="footer-link text-gray-400 hover:text-red-500 transition-colors" id="helpBtn">
                        <i class="ri-question-line text-xl"></i>
                    </a>
                    <a href="#" class="footer-link text-gray-400 hover:text-red-500 transition-colors" id="infoBtn">
                        <i class="ri-information-line text-xl"></i>
                    </a>
                </div>
            </div>
        </div>
    </footer>
    
    <!-- Help Modal -->
    <div id="helpModal" class="modal">
        <div class="modal-content card rounded-xl p-6">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-xl font-semibold dark:text-white">
                    <i class="ri-question-line mr-2 text-blue-500 dark:text-red-500"></i>
                    Help & Usage Guide
                </h3>
                <button class="modal-close text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
                    <i class="ri-close-line text-xl"></i>
                </button>
            </div>
            <div class="text-gray-800 dark:text-gray-300 space-y-4">
                <p>OSINT Assistant is a powerful tool for gathering and analyzing open-source intelligence.</p>
                
                <div class="info-panel p-4 rounded-lg mt-2">
                    <h4 class="font-medium text-blue-600 dark:text-red-400 mb-2">Basic Search</h4>
                    <p>Enter your query in the search box and click "Search" to begin. The tool will gather relevant information from various sources.</p>
                </div>
                
                <div class="info-panel p-4 rounded-lg mt-2">
                    <h4 class="font-medium text-blue-600 dark:text-red-400 mb-2">Advanced Options</h4>
                    <p>Click on "Advanced Options" to customize your search with your own API key or adjust the number of results returned.</p>
                </div>
                
                <div class="info-panel p-4 rounded-lg mt-2">
                    <h4 class="font-medium text-blue-600 dark:text-red-400 mb-2">Analysis</h4>
                    <p>Click on any search result to view detailed analysis including source credibility, sentiment analysis, and entity relationships.</p>
                </div>
                
                <div class="info-panel p-4 rounded-lg mt-2">
                    <h4 class="font-medium text-blue-600 dark:text-red-400 mb-2">Theme Toggle</h4>
                    <p>Use the toggle switch in the header to switch between dark and light modes based on your preference.</p>
                </div>
            </div>
        </div>
    </div>
    
    <!-- About Modal -->
    <div id="aboutModal" class="modal">
        <div class="modal-content card rounded-xl p-6">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-xl font-semibold dark:text-white">
                    <i class="ri-information-line mr-2 text-blue-500 dark:text-red-500"></i>
                    About OSINT Assistant
                </h3>
                <button class="modal-close text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
                    <i class="ri-close-line text-xl"></i>
                </button>
            </div>
            <div class="text-gray-800 dark:text-gray-300 space-y-4">
                <p>OSINT Assistant is an AI-enhanced tool designed for intelligence professionals, researchers, and security analysts.</p>
                
                <div class="info-panel p-4 rounded-lg mt-2">
                    <h4 class="font-medium text-blue-600 dark:text-red-400 mb-2">Features</h4>
                    <ul class="list-disc pl-5 space-y-1">
                        <li>Web scraping and data collection from multiple sources</li>
                        <li>AI-powered content analysis</li>
                        <li>Source credibility assessment</li>
                        <li>Entity extraction and relationship mapping</li>
                        <li>Sentiment analysis</li>
                    </ul>
                </div>
                
                <div class="info-panel p-4 rounded-lg mt-2">
                    <h4 class="font-medium text-blue-600 dark:text-red-400 mb-2">Privacy & Security</h4>
                    <p>All searches are conducted securely. No personal data is stored permanently. API keys, when provided, are used only for the current session and are not saved.</p>
                </div>
                
                <div class="mt-6 text-center">
                    <p class="text-sm text-gray-500 dark:text-gray-400">OSINT Assistant &copy; {{ current_year }}</p>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Toggle advanced options
        document.getElementById('advancedToggle').addEventListener('click', function() {
            const advancedOptions = document.getElementById('advancedOptions');
            const toggleIcon = document.getElementById('toggleIcon');
            
            if (advancedOptions.classList.contains('hidden')) {
                advancedOptions.classList.remove('hidden');
                toggleIcon.classList.add('rotate-90');
            } else {
                advancedOptions.classList.add('hidden');
                toggleIcon.classList.remove('rotate-90');
            }
        });
        
        // Theme toggle functionality
        const themeToggle = document.getElementById('themeToggle');
        
        function setTheme(isDark) {
            if (isDark) {
                document.body.classList.add('dark');
                document.body.classList.remove('light');
                localStorage.setItem('theme', 'dark');
            } else {
                document.body.classList.add('light');
                document.body.classList.remove('dark');
                localStorage.setItem('theme', 'light');
            }
        }
        
        themeToggle.addEventListener('change', function() {
            setTheme(this.checked);
        });
        
        // Check for saved theme preference
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            if (savedTheme === 'light') {
                themeToggle.checked = false;
                setTheme(false);
            } else {
                themeToggle.checked = true;
                setTheme(true);
            }
        } else {
            // Default to dark theme if no preference is saved
            setTheme(true);
        }
        
        // Modal functionality
        const helpBtn = document.getElementById('helpBtn');
        const infoBtn = document.getElementById('infoBtn');
        const helpModal = document.getElementById('helpModal');
        const aboutModal = document.getElementById('aboutModal');
        const closeButtons = document.querySelectorAll('.modal-close');
        
        function openModal(modal) {
            modal.classList.add('show');
        }
        
        function closeModal(modal) {
            modal.classList.remove('show');
        }
        
        helpBtn.addEventListener('click', function(e) {
            e.preventDefault();
            openModal(helpModal);
        });
        
        infoBtn.addEventListener('click', function(e) {
            e.preventDefault();
            openModal(aboutModal);
        });
        
        closeButtons.forEach(button => {
            button.addEventListener('click', function() {
                const modal = this.closest('.modal');
                closeModal(modal);
            });
        });
        
        window.addEventListener('click', function(e) {
            if (e.target.classList.contains('modal')) {
                closeModal(e.target);
            }
        });
        
        // Add Remixicon CSS
        const linkElement = document.createElement('link');
        linkElement.rel = 'stylesheet';
        linkElement.href = 'https://cdn.jsdelivr.net/npm/remixicon@2.5.0/fonts/remixicon.css';
        document.head.appendChild(linkElement);
    </script>
</body>
</html>
"""

# Store session data (normally you'd use a proper database)
session_results = {}

@app.route('/', methods=['GET'])
def index():
    """Render the main application page"""
    return render_template_string(APP_HTML, 
                                  results=None, 
                                  selected_result=None, 
                                  selected_analysis=None,
                                  query=None,
                                  is_loading=False,
                                  error=None,
                                  current_year=datetime.now().year)

@app.route('/search', methods=['POST'])
def search():
    """Handle search form submission"""
    # Get form data
    query = request.form.get('query')
    api_key = request.form.get('api_key', '')
    num_results = int(request.form.get('num_results', 10))
    
    if not query:
        return render_template_string(APP_HTML, 
                                      results=None, 
                                      selected_result=None, 
                                      selected_analysis=None,
                                      query=None,
                                      is_loading=False,
                                      error="No query provided",
                                      current_year=datetime.now().year)
    
    try:
        # Initialize the OSINT Assistant
        assistant = OSINTAssistant(api_key=api_key if api_key else None)
        
        # Perform the search
        search_results = assistant.search_web(query, num_results)
        
        # Analyze results
        for item in assistant.collected_data:
            analysis = assistant.analyze_content(item["url"])
        
        # Create the report
        report = {
            "collected_data": assistant.collected_data,
            "analysis_results": assistant.analysis_results,
            "query_info": {
                "query": query,
                "results_requested": num_results,
                "results_found": len(assistant.collected_data)
            }
        }
        
        # Store in session
        session_id = str(int(time.time()))
        session_results[session_id] = report
        
        # Redirect to the results page
        return redirect(f'/results/{session_id}')
        
    except Exception as e:
        return render_template_string(APP_HTML, 
                                      results=None, 
                                      selected_result=None, 
                                      selected_analysis=None,
                                      query=query,
                                      is_loading=False,
                                      error=str(e),
                                      current_year=datetime.now().year)

@app.route('/results/<session_id>', methods=['GET'])
def results(session_id):
    """Show search results"""
    if session_id not in session_results:
        return redirect('/')
    
    results = session_results[session_id]
    
    return render_template_string(APP_HTML, 
                                  results=results, 
                                  selected_result=None, 
                                  selected_analysis=None,
                                  query=results['query_info']['query'],
                                  is_loading=False,
                                  error=None,
                                  selected_url=None,
                                  session_id=session_id,
                                  current_year=datetime.now().year)

@app.route('/results/<session_id>/<int:result_index>', methods=['GET'])
def search_results(session_id, result_index):
    """Show a specific search result with analysis"""
    if session_id not in session_results:
        return redirect('/')
    
    results = session_results[session_id]
    
    if result_index >= len(results['collected_data']):
        return redirect(f'/results/{session_id}')
    
    selected_result = results['collected_data'][result_index]
    selected_analysis = results['analysis_results'].get(selected_result['url'])
    
    return render_template_string(APP_HTML, 
                                  results=results, 
                                  selected_result=selected_result, 
                                  selected_analysis=selected_analysis,
                                  query=results['query_info']['query'],
                                  is_loading=False,
                                  error=None,
                                  selected_url=selected_result['url'],
                                  session_id=session_id,
                                  current_year=datetime.now().year)

@app.route('/api/search', methods=['POST'])
def api_search():
    """API endpoint to perform OSINT search and analysis"""
    data = request.json
    query = data.get('query')
    num_results = data.get('num_results', 10)
    api_key = data.get('api_key', None)
    
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    try:
        # Initialize the OSINT Assistant
        assistant = OSINTAssistant(api_key=api_key)
        
        # Perform the search
        search_results = assistant.search_web(query, num_results)
        
        # Analyze results
        for item in assistant.collected_data:
            analysis = assistant.analyze_content(item["url"])
        
        # Create the report
        report = {
            "collected_data": assistant.collected_data,
            "analysis_results": assistant.analysis_results,
            "query_info": {
                "query": query,
                "results_requested": num_results,
                "results_found": len(assistant.collected_data)
            }
        }
        
        return jsonify(report)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 