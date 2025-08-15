import chalk from 'chalk';

export class Logger {
  constructor(verbose = false) {
    this.verbose = verbose;
  }
  
  info(message) {
    console.log(message);
  }
  
  success(message) {
    console.log(chalk.green(message));
  }
  
  warning(message) {
    console.log(chalk.yellow(message));
  }
  
  error(message) {
    console.error(chalk.red(message));
  }
  
  debug(message) {
    if (this.verbose) {
      console.log(chalk.gray(message));
    }
  }
  
  step(message) {
    console.log(chalk.blue(message));
  }
}