/**
 * Jenkins CI/CD Pipeline — wow-dbc-tool
 *
 * 项目范围: 魔兽世界 3.3.5 DBC 文件操作工具（面向 Agent）
 * 触发方式: 手动触发 / TGit Webhook
 *
 * 阶段:
 *   1. 环境准备 — Python 3.9+ + venv + pip
 *   2. 代码静态检查 — ruff（非阻塞）
 *   3. 代码格式化检查 — black（非阻塞）
 *   4. 类型检查 — mypy（非阻塞）
 *   5. 单元测试 — pytest + coverage（阻塞）
 *   6. 包构建验证 — python -m build（阻塞，确保 setuptools 配置正确）
 */

pipeline {
    agent {
        docker {
            image 'python:3.11-slim'
            // 如需将宿主机目录挂载到容器，可在此添加 args
            // args '-v /host/path:/container/path'
        }
    }

    options {
        timestamps()
        timeout(time: 20, unit: 'MINUTES')
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    // ============================================================
    //  环境变量
    // ============================================================
    environment {
        PYPI_MIRROR  = 'https://mirrors.cloud.tencent.com/pypi/simple'
        PYPI_HOST    = 'mirrors.cloud.tencent.com'
        SRC_DIR      = 'src'
        TESTS_DIR    = 'tests'
        DEPLOY_ENV   = "${env.BRANCH_NAME == 'main' ? 'production' : 'staging'}"
    }

    stages {

        // ============================================================
        //  Stage 1: 环境准备
        // ============================================================
        stage('环境准备') {
            steps {
                echo """========================================
Pipeline:    wow-dbc-tool
Branch:      ${env.BRANCH_NAME ?: 'N/A'}
Build:       ${env.BUILD_NUMBER}
Deploy Env:  ${env.DEPLOY_ENV}
========================================"""

                // python:3.11-slim 不包含 git，需先安装
                // python:3.11-slim does not include git, install it first
                sh 'apt-get update -qq && apt-get install -y -qq git'

                sh 'bash cicd/scripts/setup-python.sh'

                script {
                    // 加载 setup-python.sh 生成的环境变量
                    def envVars = readProperties file: '.env.pipeline'
                    env.PYTHON = envVars.PYTHON
                    env.PIP    = envVars.PIP

                    echo "Python: ${env.PYTHON}"
                    echo "pip:    ${env.PIP}"
                }

                // 安装项目 + dev 依赖（editable 模式，带 coverage 信息）
                sh '''
                    ${PIP} install -e ".[dev]" \
                        -i ${PYPI_MIRROR} --trusted-host ${PYPI_HOST}
                '''
            }
        }

        // ============================================================
        //  Stage 2: 代码静态检查（ruff — 非阻塞）
        // ============================================================
        stage('代码静态检查') {
            steps {
                script {
                    try {
                        sh '''
                            mkdir -p report
                            ${PYTHON} -m ruff check . \
                                --output-format junit > report/ruff-results.xml
                        '''
                    } catch (Exception e) {
                        echo "Ruff check found issues (non-blocking): ${e.getMessage()}"
                        currentBuild.result = 'UNSTABLE'
                    }
                }
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: "report/ruff-results.xml"
                }
            }
        }

        // ============================================================
        //  Stage 3: 代码格式化检查（black — 非阻塞）
        // ============================================================
        stage('代码格式化检查') {
            steps {
                script {
                    try {
                        sh '''
                            ${PYTHON} -m black --check ${SRC_DIR} ${TESTS_DIR}/
                        '''
                    } catch (Exception e) {
                        echo "Black formatting check failed (non-blocking): ${e.getMessage()}"
                        echo "提示: 运行 'black ${SRC_DIR} ${TESTS_DIR}/' 自动修复格式化问题"
                        currentBuild.result = 'UNSTABLE'
                    }
                }
            }
        }

        // ============================================================
        //  Stage 4: 类型检查（mypy — 非阻塞）
        // ============================================================
        stage('类型检查') {
            steps {
                script {
                    try {
                        sh '''
                            mkdir -p report
                            ${PYTHON} -m mypy ${SRC_DIR}/ \
                                --junit-xml report/mypy-results.xml
                        '''
                    } catch (Exception e) {
                        echo "MyPy check found issues (non-blocking): ${e.getMessage()}"
                        currentBuild.result = 'UNSTABLE'
                    }
                }
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: "report/mypy-results.xml"
                }
            }
        }

        // ============================================================
        //  Stage 5: 单元测试（pytest + coverage — 阻塞）
        // ============================================================
        stage('单元测试') {
            steps {
                script {
                    try {
                        sh '''
                            mkdir -p report
                            ${PYTHON} -m pytest ${TESTS_DIR}/ \
                                -v --tb=short \
                                --junitxml=report/test-results.xml
                        '''
                    } catch (Exception e) {
                        env.FAIL_REASON = "wow-dbc-tool - pytest 测试失败"
                        error(env.FAIL_REASON)
                    }
                }
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: "report/test-results.xml"
                    publishHTML(target: [
                        reportDir: "htmlcov",
                        reportFiles: 'index.html',
                        reportName: 'Coverage Report',
                        keepAll: true
                    ])
                }
            }
        }

        // ============================================================
        //  Stage 6: 包构建验证（python -m build — 阻塞）
        // ============================================================
        stage('包构建验证') {
            steps {
                script {
                    try {
                        sh '''
                            rm -rf dist/ build/
                            ${PYTHON} -m build
                            echo ">>> 包构建成功"
                            ls -lh dist/
                        '''
                    } catch (Exception e) {
                        env.FAIL_REASON = "wow-dbc-tool - 包构建失败，请检查 pyproject.toml 配置"
                        error(env.FAIL_REASON)
                    }
                }
            }
        }
    }

    // ============================================================
    //  Post Actions
    // ============================================================
    post {
        success {
            echo 'wow-dbc-tool Pipeline 执行成功!'
        }
        failure {
            echo 'wow-dbc-tool Pipeline 执行失败，请检查日志!'
            script {
                if (env.FAIL_REASON) {
                    echo ">>> 失败原因: ${env.FAIL_REASON}"
                }
            }
        }
        cleanup {
            cleanWs(notFailBuild: true, deleteDirs: true)
        }
    }
}
