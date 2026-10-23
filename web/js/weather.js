/**
 * weather.js - 天气组件
 * 
 * 在侧边栏底部显示当前日期、城市和天气信息。
 * 使用浏览器定位获取经纬度，通过 Nominatim 反地理编码获取城市名，
 * 然后调用后端 /api/weather 获取天气数据。
 */

// 星期映射
const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六'];

/**
 * 格式化日期为 "YYYY年MM月DD日 星期X"
 */
function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const weekday = WEEKDAYS[date.getDay()];
    return `${year}年${month}月${day}日 星期${weekday}`;
}

/**
 * 显示天气加载状态
 */
function showWeatherLoading() {
    document.getElementById('weatherLoading').style.display = 'flex';
    document.getElementById('weatherContent').style.display = 'none';
    document.getElementById('weatherError').style.display = 'none';
}

/**
 * 显示天气内容
 */
function showWeatherContent(data) {
    document.getElementById('weatherLoading').style.display = 'none';
    document.getElementById('weatherContent').style.display = 'block';
    document.getElementById('weatherError').style.display = 'none';
    
    // 显示当前日期
    const now = new Date();
    document.getElementById('weatherDate').textContent = formatDate(now);
    
    // 显示城市（优先使用中文城市名）
    document.getElementById('weatherCity').textContent = `📍 ${data.city_zh || data.city}`;
    
    // 显示温度
    document.getElementById('weatherTemp').textContent = `${data.temperature}°C`;
    
    // 显示天气状况（如果有数据）
    const conditionEl = document.getElementById('weatherCondition');
    if (data.condition && data.condition !== '未知') {
        conditionEl.textContent = data.condition;
        conditionEl.style.display = 'inline-block';
    } else {
        conditionEl.style.display = 'none';
    }
    
    // 显示湿度、风力和空气质量
    document.getElementById('weatherHumidity').textContent = `💧 ${data.humidity}%`;
    document.getElementById('weatherWind').textContent = `🌬️ ${data.wind} m/s`;
    
    // 显示空气质量（使用欧盟标准）
    const airQualityEl = document.getElementById('weatherQuality');
    if (data.air_quality && data.air_quality.level) {
        const aqiDisplay = data.air_quality.aqi_eu !== null ? data.air_quality.aqi_eu : '-';
        const pm25Display = data.air_quality.pm25 !== null ? data.air_quality.pm25 : '-';
        airQualityEl.textContent = `🌫️ ${data.air_quality.level}`;
        airQualityEl.title = `EU AQI: ${aqiDisplay} | PM2.5: ${pm25Display} μg/m³`;
    } else {
        airQualityEl.textContent = '🌫️ -';
    }
}

/**
 * 显示天气错误
 */
function showWeatherError(message) {
    document.getElementById('weatherLoading').style.display = 'none';
    document.getElementById('weatherContent').style.display = 'none';
    document.getElementById('weatherError').style.display = 'block';
    document.getElementById('weatherError').textContent = message;
}

/**
 * 通过经纬度获取城市名（使用 Nominatim 反地理编码）
 */
async function getCityFromCoords(lat, lon) {
    try {
        const response = await fetch(
            `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&zoom=10&accept-language=zh`,
            {
                headers: {
                    'User-Agent': 'AI-Agent-Writer/1.0'
                }
            }
        );
        
        if (!response.ok) {
            throw new Error('反地理编码请求失败');
        }
        
        const data = await response.json();
        
        // 尝试从 address 中提取城市名
        const address = data.address || {};
        const city = address.city || address.town || address.village || 
                     address.county || address.state || address.province;
        
        if (!city) {
            throw new Error('无法识别城市名');
        }
        
        return city;
    } catch (error) {
        console.error('反地理编码失败:', error);
        throw error;
    }
}

/**
 * 获取默认城市（从配置文件）
 */
async function getDefaultCity() {
    try {
        const response = await fetch('/api/weather/default-city');
        if (!response.ok) {
            throw new Error('获取默认城市失败');
        }
        const data = await response.json();
        return data.city;
    } catch (error) {
        console.error('获取默认城市失败:', error);
        return '北京'; // 最终降级
    }
}

/**
 * 调用后端天气 API
 */
async function fetchWeather(city) {
    const response = await fetch(`/api/weather?city=${encodeURIComponent(city)}`);
    
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || '获取天气失败');
    }
    
    return await response.json();
}

/**
 * 加载天气信息的主函数
 */
async function loadWeather() {
    showWeatherLoading();
    
    let city = null;
    
    // 第一步：尝试浏览器定位
    if ('geolocation' in navigator) {
        try {
            const position = await new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(resolve, reject, {
                    timeout: 5000,
                    maximumAge: 300000 // 5分钟内缓存
                });
            });
            
            const { latitude, longitude } = position.coords;
            console.log(`定位成功: ${latitude}, ${longitude}`);
            
            // 第二步：反地理编码获取城市
            city = await getCityFromCoords(latitude, longitude);
            console.log(`识别城市: ${city}`);
        } catch (error) {
            console.warn('浏览器定位失败，使用默认城市:', error.message);
        }
    } else {
        console.warn('浏览器不支持地理定位，使用默认城市');
    }
    
    // 第三步：如果定位失败，使用默认城市
    if (!city) {
        city = await getDefaultCity();
        console.log(`使用默认城市: ${city}`);
    }
    
    // 第四步：获取天气数据
    try {
        const weatherData = await fetchWeather(city);
        showWeatherContent(weatherData);
    } catch (error) {
        console.error('获取天气失败:', error);
        showWeatherError(`❌ ${error.message}`);
    }
}

// 页面加载完成后初始化天气组件
document.addEventListener('DOMContentLoaded', () => {
    loadWeather();
});
